from pathlib import Path

from seti_ai import pool


def test_share_follows_weights_and_is_fixed():
    entries = [{"name": "a", "kind": "self", "weight": 2}, {"name": "b", "kind": "bot", "bot": "greedy", "weight": 1}]
    out = pool.share(entries, 12)
    assert [e["name"] for e in out].count("a") == 8
    assert out == pool.share(entries, 12)


def test_remember_keeps_last_versions(tmp_path: Path):
    entries = pool.load(tmp_path / "none.json")
    for i in range(10):
        entries = pool.remember(entries, f"v{i:03d}", f"m/v{i:03d}.pt")
    past = [e for e in entries if e.get("past")]
    assert len(past) == pool.KEEP_PAST
    assert past[-1]["name"] == "past:v009"
    pool.save(tmp_path / "pool.json", entries)
    assert pool.load(tmp_path / "pool.json") == entries
