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
