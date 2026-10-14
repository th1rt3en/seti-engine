"""Signed requests (decision D16): the engine service accepts a request only if the Worker (or the website) signed it.

Every request carries `Authorization: Bearer <JWT>`, an ES256 token with the claims
  iss  who signed ("worker" or "web"), the key is looked up by it
  iat, exp  issued and expiry (at most 120 seconds apart)
  jti  a random id, accepted once
  htm, htu  the HTTP method and path, so a token cannot be used for another request
  bsh  base64url of the SHA-256 of the request body, so the body cannot be changed.
The trusted public keys are in the environment variable ENGINE_TRUSTED_KEYS, a JSON object {"worker": "<PEM>", "web": "<PEM>"}.
Without it the service is open (development), except on Cloud Run (the variable K_SERVICE is set) where it refuses every
request but /health, so a deploy that forgot the keys does not run unprotected.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.serialization import load_pem_public_key

MAX_LIFETIME = 120
SKEW = 30


class Unauthorized(Exception):
    pass


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def trusted_keys() -> dict[str, ec.EllipticCurvePublicKey] | None:
    """The keys from the environment; None when the service is open (development)."""
    raw = os.environ.get("ENGINE_TRUSTED_KEYS", "")
    if raw == "":
        return {} if os.environ.get("K_SERVICE") else None
    keys: dict[str, ec.EllipticCurvePublicKey] = {}
    for issuer, pem in json.loads(raw).items():
        key = load_pem_public_key(str(pem).replace("\\n", "\n").encode())
        if not isinstance(key, ec.EllipticCurvePublicKey):
            raise ValueError(f"the key of {issuer} is not an EC key")
        keys[issuer] = key
    return keys


class ReplayCache:
    """The ids of the tokens seen lately. One per process: a token cannot be replayed to the same instance within its short life."""

    def __init__(self) -> None:
        self._seen: dict[str, float] = {}

    def add(self, jti: str, expires: float, now: float) -> bool:
        for k in [k for k, e in self._seen.items() if e < now]:
            del self._seen[k]
        if jti in self._seen:
            return False
        self._seen[jti] = expires
        return True


def verify(
    authorization: str | None,
    method: str,
    path: str,
    body: bytes,
    keys: dict[str, ec.EllipticCurvePublicKey],
    cache: ReplayCache,
    now: float | None = None,
) -> str:
    """Check a request; returns the issuer or raises Unauthorized."""
    now = time.time() if now is None else now
    if authorization is None or not authorization.startswith("Bearer "):
        raise Unauthorized("missing token")
    parts = authorization[7:].split(".")
    if len(parts) != 3:
        raise Unauthorized("malformed token")
    try:
        header = json.loads(_b64d(parts[0]))
        claims: dict[str, Any] = json.loads(_b64d(parts[1]))
        signature = _b64d(parts[2])
    except ValueError as e:
        raise Unauthorized("malformed token") from e
    if header.get("alg") != "ES256":
        raise Unauthorized("wrong algorithm")
    key = keys.get(str(claims.get("iss")))
    if key is None:
        raise Unauthorized("unknown issuer")
    if len(signature) != 64:
        raise Unauthorized("bad signature")
    der = encode_dss_signature(int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big"))
    try:
        key.verify(der, f"{parts[0]}.{parts[1]}".encode(), ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as e:
        raise Unauthorized("bad signature") from e
    iat, exp, jti = claims.get("iat"), claims.get("exp"), claims.get("jti")
    if not isinstance(iat, int | float) or not isinstance(exp, int | float) or not isinstance(jti, str) or jti == "":
        raise Unauthorized("missing claims")
    if exp < now or iat > now + SKEW or exp - iat > MAX_LIFETIME:
        raise Unauthorized("expired or not yet valid")
    if claims.get("htm") != method.upper() or claims.get("htu") != path:
        raise Unauthorized("token is for another request")
    digest = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b"=").decode()
    if claims.get("bsh") != digest:
        raise Unauthorized("body does not match")
    if not cache.add(jti, float(exp), now):
        raise Unauthorized("token already used")
    return str(claims["iss"])
