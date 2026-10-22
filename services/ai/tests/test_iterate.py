"""The training of version 3 (iterate.py): self-play with the search and the games of people, a run on the processor with a hand-made brain in place of the
network's search, to see that the pieces fit, that a pause and a resume work, and that nothing starts without the owner's go."""

import json
import random
import sys
from pathlib import Path
from typing import Any

import pytest
import torch
from seti_engine.models import Options

from seti_ai import arena, bots, checkpoint, gate, iterate
from seti_ai.agent import PolicyNet, new_net, save_net
from seti_ai.brains import HeuristicBrain
from seti_ai.bundle_data import Examples
from seti_ai.bundle_search import Brain, SearchConfig

TINY = SearchConfig(samples=2, keep=1, neighbours=2, finalists=1, copies=1)
CPU = torch.device("cpu")


def heuristic_brain(net: PolicyNet) -> Brain:
    return HeuristicBrain()


@pytest.fixture(scope="module")
def archive(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("archive")
    res = arena.play_game([bots.heuristic(), bots.heuristic()], 21, random.Random(21))
    assert res.finished
    header = {"options": Options(players=2, seed=21).model_dump(), "seats": [], "rngEncoding": "exact", "id": "g1"}
    result = {"status": "finished", "result": {"reason": "completed", "ranking": [{"seat": i, "score": s} for i, s in enumerate(res.scores)]}}
    (root / "g1").mkdir()
    (root / "g1" / "replay.json").write_text(
        json.dumps({"header": header, "actions": [{"seq": i, "action": a} for i, a in enumerate(res.actions)], "result": result}), encoding="utf-8"
    )
    return root


@pytest.fixture(scope="module")
def start(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A saved version to start from, with the manifest that a version has."""
    folder = tmp_path_factory.mktemp("models") / "v001"
    folder.mkdir()
    save_net(new_net("small"), str(folder / "model.pt"))
    (folder / "manifest.json").write_text(json.dumps({"version": "v001", "evaluation": {"heuristic": {"agent_score": 30.0}}}), encoding="utf-8")
    return folder


def settings(tmp_path: Path, archive: Path | None, **kw: Any) -> iterate.Settings:
    base: dict[str, Any] = {
        "models": tmp_path / "models",
        "people": archive,
        "iterations": 1,
        "selfplay_games": 1,
        "bot_share": 1.0,
        "human_positions": 3,
        "epochs": 1,
        "batch": 32,
        "gate_games": 0,
        "eval_games": 0,
        "search": TINY,
        "log_every": 1e9,
    }
    return iterate.Settings(**{**base, **kw})


def test_a_run_makes_examples_trains_and_leaves_a_checkpoint_and_a_buffer(tmp_path: Path, archive: Path, start: Path) -> None:
    s = settings(tmp_path, archive)
    iterate.run(s, start, resume=False, brain=heuristic_brain, device=CPU)
    assert checkpoint.exists(s.models)
    rows = [json.loads(line) for line in (s.models / "metrics.jsonl").read_text(encoding="utf-8").splitlines()]
    rec = next(r for r in rows if r["kind"] == "iterate")
    assert rec["iteration"] == 1 and rec["self_play"]["games"] == 1 and rec["self_play"]["against_heuristic"]["games"] == 1
    assert rec["expert"]["positions"] == 3 and rec["data"]["choices"] > 50 and rec["data"]["positions"] > 10
    assert rec["epochs"][0]["policy_loss"] > 0
    assert [p.name for p in (s.models / "buffer").glob("*.pkl")] == ["iteration_0001.pkl"]
    kept = iterate.Buffer(s.models, 4).load()
    assert isinstance(kept, Examples) and kept.policy and kept.value


def test_a_run_goes_on_after_a_pause_from_its_checkpoint_and_its_buffer(tmp_path: Path, archive: Path, start: Path) -> None:
    s = settings(tmp_path, archive, iterations=2, buffer=1)
    iterate.run(settings(tmp_path, archive, iterations=1, buffer=1), start, resume=False, brain=heuristic_brain, device=CPU)
    iterate.run(s, start, resume=True, brain=heuristic_brain, device=CPU)
    rows = [json.loads(line) for line in (s.models / "metrics.jsonl").read_text(encoding="utf-8").splitlines() if '"iterate"' in line]
    assert [r["iteration"] for r in rows] == [1, 2]
    assert [p.name for p in (s.models / "buffer").glob("*.pkl")] == ["iteration_0002.pkl"]  # only the last iteration is kept
    assert int(torch.load(checkpoint.path(s.models), weights_only=False)["meta"]["iteration"]) == 2


def test_a_pause_in_the_middle_of_an_iteration_saves_nothing_of_it(tmp_path: Path, archive: Path, start: Path) -> None:
    s = settings(tmp_path, archive)
    net = new_net("small")
    opt = torch.optim.AdamW(net.parameters(), lr=1e-4)
    buf = iterate.Buffer(s.models, 4)
    champion = iterate.champion_of(start)
    rec = iterate.iteration(net, opt, 1, s, CPU, Examples(), buf, champion, heuristic_brain, lambda: True)
    assert rec is None
    assert not list((s.models / "buffer").glob("*.pkl")) and not (s.models / "metrics.jsonl").exists()


def test_the_champion_is_the_start_version_with_its_yardstick(start: Path) -> None:
    c = iterate.champion_of(start)
    assert c["version"] == "v001" and c["bench"] == 30.0 and c["path"].endswith("model.pt")


def test_a_promotion_writes_the_version_its_manifest_and_the_new_champion(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, start: Path) -> None:
    """The same brain on both sides is a coin flip, so the decision of the gate is forced (it has its own tests, test_gate.py): what is checked is what a
    promotion does and that the head to head is played."""
    s = settings(tmp_path, None, gate_games=2, human_positions=0)
    net = new_net("small")
    opt = torch.optim.AdamW(net.parameters(), lr=1e-4)
    champion = iterate.champion_of(start)
    monkeypatch.setattr(gate, "decide", lambda champ, h2h, bench: gate.Decision(True, "forced for the test"))
    rec = iterate.iteration(net, opt, 1, s, CPU, Examples(), iterate.Buffer(s.models, 4), champion, heuristic_brain)
    assert rec is not None and rec["saved"] == "v001" and rec["gate"]["h2h"]["games"] == 2
    assert (s.models / "v001" / "model.pt").exists()
    manifest = json.loads((s.models / "v001" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["parent"] == "v001" and manifest["approved"] is False
    assert champion["version"] == "v001" and champion["path"].endswith("model.pt")


def test_training_does_not_start_without_the_owners_go(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "argv", ["iterate", "run", "--models", str(tmp_path)])
    with pytest.raises(SystemExit) as e:
        iterate.main()
    assert "owner's go" in str(e.value)
    assert not (tmp_path / "checkpoint").exists()


def test_a_pause_is_asked_for_with_a_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "argv", ["iterate", "pause", "--models", str(tmp_path)])
    iterate.main()
    assert checkpoint.pause_requested(tmp_path)
