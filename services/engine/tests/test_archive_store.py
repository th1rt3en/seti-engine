"""The archive endpoint of the service (decision D25): only archive paths, written to ARCHIVE_DIR in development."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from seti_engine import archive_store
from seti_engine.service import app

client = TestClient(app)
GOOD = "seti-engine/games/2026/10/13/abc123/actions/0000007.json"


@pytest.mark.parametrize(
    "path",
    [
        GOOD,
        "seti-engine/games/2026/10/13/abc/header.json",
        "seti-engine/games/2026/10/13/abc/replay.json",
        "seti-engine/games/2026/10/13/abc/result.json",
    ],
)
def test_the_paths_of_an_archive_are_accepted(path: str) -> None:
    assert archive_store.valid_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "other/x.json",
        "seti-engine/games/../../etc/passwd",
        "seti-engine/games/2026/10/13/abc/../x/header.json",
        "seti-engine/games/2026/10/13/abc/notes.txt",
        "/seti-engine/games/2026/10/13/a/header.json",
    ],
)
def test_anything_else_is_refused(path: str) -> None:
    assert not archive_store.valid_path(path)
    assert client.put("/archive", json={"path": path, "body": {}}).status_code == 400


def test_a_file_is_written_and_overwritten(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path))
    assert client.put("/archive", json={"path": GOOD, "body": {"n": 1}}).json() == {"ok": True}
    assert client.put("/archive", json={"path": GOOD, "body": {"n": 2}}).status_code == 200
    assert json.loads((tmp_path / GOOD).read_text()) == {"n": 2}


def test_a_failed_write_is_a_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARCHIVE_DIR", raising=False)
    monkeypatch.setattr(archive_store, "_access_token", lambda: (_ for _ in ()).throw(OSError("no metadata server")))
    res = client.put("/archive", json={"path": GOOD, "body": {}})
    assert res.status_code == 503 and res.json()["error"] == "archive_failed"


def test_an_error_report_is_stored_under_the_day_with_a_made_up_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path))
    res = client.put("/errors", json={"source": "worker", "message": "boom", "detail": {"route": "/games/x", "stack": "s" * 20000}})
    assert res.status_code == 200
    path = res.json()["path"]
    assert archive_store.valid_error_path(path) and path.startswith("seti-engine/errors/") and "-worker-" in path
    saved = json.loads((tmp_path / path).read_text(encoding="utf-8"))
    assert saved["source"] == "worker" and saved["message"] == "boom" and len(saved["detail"]["stack"]) == 6000  # long text is cut
    again = client.put("/errors", json={"source": "worker", "message": "boom"}).json()["path"]
    assert again != path  # a new object each time: nothing is overwritten


def test_error_reports_cannot_name_their_own_path_or_a_strange_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path))
    path = client.put("/errors", json={"source": "../../etc", "message": "x"}).json()["path"]
    assert "-unknown-" in path  # an odd source is replaced, and the path is always the engine's own
    assert not archive_store.valid_error_path("seti-engine/errors/../games/x.json")
    assert not archive_store.valid_error_path("seti-engine/errors/2026-10-19/a/b.json")
    assert archive_store.error_path("web", now=0).startswith("seti-engine/errors/1970-01-01/000000-web-")


def test_an_unexpected_error_of_the_engine_is_stored_and_answered_with_a_plain_500(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path))
    from seti_engine import service

    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("a rule broke")

    monkeypatch.setattr(service.engine, "start", boom)
    res = TestClient(app, raise_server_exceptions=False).post("/new", json={"options": {"players": 2, "seed": 1}})
    assert res.status_code == 500 and res.json()["error"] == "internal"
    files = list((tmp_path / "seti-engine" / "errors").rglob("*.json"))
    assert len(files) == 1 and "a rule broke" in json.loads(files[0].read_text(encoding="utf-8"))["message"]
