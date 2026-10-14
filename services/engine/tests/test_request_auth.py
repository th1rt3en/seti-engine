"""Signed requests to the service (decision D16)."""

import base64
import hashlib
import json
import time
from collections.abc import Iterator

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from fastapi.testclient import TestClient

from seti_engine.service import app

b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()  # noqa: E731
KEY = ec.generate_private_key(ec.SECP256R1())
OTHER = ec.generate_private_key(ec.SECP256R1())
PUBLIC = KEY.public_key()
PEM = PUBLIC.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def token(method: str, path: str, body: bytes, *, key: ec.EllipticCurvePrivateKey = KEY, iss: str = "worker", **over: object) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": iss, "iat": now, "exp": now + 30, "jti": b64(hashlib.sha256(str(time.time_ns()).encode()).digest()),
        "htm": method, "htu": path, "bsh": b64(hashlib.sha256(body).digest()),
    }  # fmt: skip
    claims.update(over)
    head = b64(json.dumps({"alg": "ES256", "typ": "JWT"}).encode())
    payload = b64(json.dumps(claims).encode())
    r, s = decode_dss_signature(key.sign(f"{head}.{payload}".encode(), ec.ECDSA(hashes.SHA256())))
    return f"{head}.{payload}.{b64(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"


@pytest.fixture
def secured(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("ENGINE_TRUSTED_KEYS", json.dumps({"worker": PEM}))
    yield TestClient(app)


def call(client: TestClient, tok: str | None, payload: dict[str, object] | None = None, path: str = "/legal"):  # type: ignore[no-untyped-def]
    body = json.dumps(payload if payload is not None else {"options": {"players": 2, "seed": 3}}).encode()
    headers = {"content-type": "application/json", **({"authorization": f"Bearer {tok}"} if tok else {})}
    return client.post(path, content=body, headers=headers), body


def signed(client: TestClient, path: str = "/new", payload: dict[str, object] | None = None, **over: object):  # type: ignore[no-untyped-def]
    body = json.dumps(payload if payload is not None else {"options": {"players": 2, "seed": 3}}).encode()
    tok = token("POST", path, body, **over)  # type: ignore[arg-type]
    return client.post(path, content=body, headers={"content-type": "application/json", "authorization": f"Bearer {tok}"})


def test_a_signed_request_is_served_and_health_is_open(secured: TestClient) -> None:
    assert signed(secured).status_code == 200
    assert secured.get("/health").status_code == 200


def test_unsigned_and_badly_signed_requests_are_refused(secured: TestClient) -> None:
    assert secured.post("/new", json={"options": {"players": 2}}).status_code == 401
    assert signed(secured, key=OTHER).status_code == 401  # signed by a key that is not trusted
    assert signed(secured, iss="stranger").status_code == 401


def test_a_token_is_good_for_one_request_one_body_one_use(secured: TestClient) -> None:
    body = json.dumps({"options": {"players": 2, "seed": 3}}).encode()
    tok = token("POST", "/new", body)
    headers = {"content-type": "application/json", "authorization": f"Bearer {tok}"}
    assert secured.post("/new", content=body, headers=headers).status_code == 200
    assert secured.post("/new", content=body, headers=headers).status_code == 401  # replayed
    tok = token("POST", "/new", body)
    other = json.dumps({"options": {"players": 4, "seed": 3}}).encode()  # another body
    assert (
        secured.post("/new", content=other, headers={"content-type": "application/json", "authorization": f"Bearer {tok}"}).status_code
        == 401
    )
    tok = token("POST", "/new", body)
    assert (
        secured.post("/legal", content=body, headers={"content-type": "application/json", "authorization": f"Bearer {tok}"}).status_code
        == 401
    )  # another path


def test_expired_and_far_future_tokens_are_refused(secured: TestClient) -> None:
    now = int(time.time())
    assert signed(secured, iat=now - 100, exp=now - 50).status_code == 401
    assert signed(secured, iat=now + 500, exp=now + 520).status_code == 401
    assert signed(secured, iat=now, exp=now + 3600).status_code == 401  # too long a life


def test_the_archive_endpoint_is_protected_too(secured: TestClient) -> None:
    res = secured.put("/archive", json={"path": "seti-engine/games/2026/10/13/a/header.json", "body": {}})
    assert res.status_code == 401


def test_open_in_development_and_closed_on_cloud_run_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENGINE_TRUSTED_KEYS", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)
    client = TestClient(app)
    assert client.post("/new", json={"options": {"players": 2, "seed": 3}}).status_code == 200
    monkeypatch.setenv("K_SERVICE", "seti-engine")
    assert client.post("/new", json={"options": {"players": 2, "seed": 3}}).status_code == 401
    assert client.get("/health").status_code == 200
