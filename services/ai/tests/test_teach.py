"""The copy of a saved model: a game in which a model plays through the inference server is recorded (inference only, a few steps)."""

from __future__ import annotations

from pathlib import Path

from seti_ai import arena, train
from seti_ai.agent import new_net, save_net
from seti_ai.server import Client, start_server


def test_teach_job_records_both_seats(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    path = str(tmp_path / "m.pt")
    save_net(new_net("small"), path)
    proc, req_q, resp_qs, ctl_q, _ = start_server(1, "cpu")
    try:
        train.load_into_server(req_q, ctl_q, path, "teacher")
        train._STATE["client"] = Client(0, req_q, resp_qs[0])
        monkeypatch.setattr(arena, "MAX_STEPS", 30)
        out = train.play_job({"kind": "teach", "seed": 3})
        assert len(out["trajs"]) == 2 and all(len(t["steps"]) > 0 for t in out["trajs"])
        out = train.play_job({"kind": "teach", "opp": "heuristic", "seat": 1, "seed": 3})
        assert len(out["trajs"]) == 1
    finally:
        req_q.put(("stop",))
        proc.join(timeout=10)
