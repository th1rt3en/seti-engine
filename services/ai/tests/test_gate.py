from pathlib import Path

from seti_ai import gate


def h2h(win_rate: float, mine: float, theirs: float, games: int = 100) -> dict[str, float]:
    return {"win_rate": win_rate, "agent_score": mine, "bot_score": theirs, "games": games}


CHAMPION = {"version": "v001", "path": "x", "bench": 100.0}


def test_the_first_version_is_promoted() -> None:
    assert gate.decide(None, None, 20.0).promote


def test_a_candidate_that_beats_the_champion_and_holds_the_yardstick_is_promoted() -> None:
    assert gate.decide(CHAMPION, h2h(0.6, 110, 100), 105.0).promote


def test_too_few_wins_is_not_enough() -> None:
    d = gate.decide(CHAMPION, h2h(0.54, 110, 100), 105.0)
    assert not d.promote and "55%" in d.reason


def test_winning_without_scoring_more_is_not_enough() -> None:
    assert not gate.decide(CHAMPION, h2h(0.6, 100, 100), 105.0).promote
    assert not gate.decide(CHAMPION, h2h(0.6, 90, 100), 105.0).promote


def test_beating_a_weak_champion_while_falling_behind_on_the_yardstick_is_not_promoted() -> None:
    # two weak versions that keep beating each other: the fixed yardstick (heuristic v3) says the candidate is worse than the champion was
    d = gate.decide(CHAMPION, h2h(0.7, 60, 40), 80.0)
    assert not d.promote and "yardstick" in d.reason
    assert gate.decide(CHAMPION, h2h(0.7, 60, 40), 95.0).promote  # within the tolerance of 5 points


def test_low_scores_are_flagged_against_the_reference_of_250() -> None:
    assert gate.is_low(100.0) and not gate.is_low(130.0)
    assert gate.share_of_reference(125.0).startswith("50%")


def test_the_metrics_are_one_json_line_each(tmp_path: Path) -> None:
    gate.log_metrics(tmp_path, {"round": 1, "own_score": 42.0})
    gate.log_metrics(tmp_path, {"round": 2, "own_score": 45.0})
    lines = (tmp_path / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and '"reference_score": 250.0' in lines[0]


def test_the_head_to_head_plays_the_candidate_against_the_champion_through_the_server(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Inference only: two small networks play a few steps of two games; nothing is trained."""
    from seti_ai import arena, train
    from seti_ai.agent import new_net, save_net
    from seti_ai.server import Client, start_server

    for name in ("main", "champion"):
        save_net(new_net("small"), str(tmp_path / f"{name}.pt"))
    proc, req_q, resp_qs, ctl_q, _ = start_server(1, "cpu")
    try:
        train.load_into_server(req_q, ctl_q, str(tmp_path / "main.pt"), "main")
        train.load_into_server(req_q, ctl_q, str(tmp_path / "champion.pt"), "champion")
        train._STATE["client"] = Client(0, req_q, resp_qs[0])
        monkeypatch.setattr(arena, "MAX_STEPS", 25)
        monkeypatch.setattr(train, "run_games", lambda pool, jobs: [train.play_job(j) for j in jobs])
        out = train.evaluate_h2h(None, games=4)
        assert out["games"] == 4 and 0.0 <= out["win_rate"] <= 1.0
        assert set(out) == {"games", "agent_score", "bot_score", "win_rate"}
        bench = train.evaluate(None, 2, opponents=("greedy",), model="champion")  # the champion measured against a bot, with its own network
        assert bench["greedy"]["games"] == 2
    finally:
        req_q.put(("stop",))
        proc.join(timeout=10)
