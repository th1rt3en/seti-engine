"""The model in the lobby (lobby.py): the replay of a game from its log, the move of a seat with the plan handed back and forth, and the service."""

import json
import random
from pathlib import Path

import pytest
from seti_engine import engine
from seti_engine.models import Options
from seti_engine.projection import to_act

from seti_ai import arena, bots
from seti_ai.brains import HeuristicBrain
from seti_ai.bundle_search import SearchConfig
from seti_ai.lobby import Lobby, NoSuchModel, NotYourTurn, approved_versions, replay

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "solo-289.json").read_text(encoding="utf-8"))
SMALL = SearchConfig(samples=2, keep=1, neighbours=2, finalists=2, copies=1)


def lobby() -> Lobby:
    return Lobby({"v001": HeuristicBrain()}, SMALL)


def a_game(seed: int, n: int) -> tuple[Options, list[dict]]:  # type: ignore[type-arg]
    options = Options(players=2, seed=seed)
    res = arena.play_game([bots.heuristic(), bots.heuristic()], seed, random.Random(seed), {})
    return options, res.actions[:n]


def test_the_replay_of_a_log_is_the_game_as_it_was_played() -> None:
    state, history, _ = replay(Options(**FIXTURE["options"]), FIXTURE["actions"], FIXTURE["rng_encoding"])
    assert state.phase == "finished"
    assert state.final_scores[0]["total"] == FIXTURE["final"][0]
    undone = sum(1 for a in FIXTURE["actions"] if a["type"] == "undo")
    assert len(history) == len(FIXTURE["actions"]) - 2 * undone, "a move that was taken back is not remembered"


def test_the_seat_that_is_to_act_gets_a_legal_move_and_the_rest_of_its_bundle() -> None:
    options, actions = a_game(11, 40)
    state, _, _ = replay(options, actions)
    seat = to_act(state)
    assert seat is not None
    reply = lobby().move("v001", options, actions, seat, [])
    assert reply.searched
    assert reply.action in engine.legal_moves(state)
    # the plan is the rest of the bundle: playing the move and then the plan is legal all the way
    cur = state
    for move in [reply.action, *reply.plan]:
        assert move in engine.legal_moves(cur)
        cur = engine.apply(cur, move).state


def test_a_plan_that_the_game_still_asks_for_is_followed_without_a_new_search() -> None:
    options, actions = a_game(12, 40)
    state, _, _ = replay(options, actions)
    seat = to_act(state)
    assert seat is not None
    first = lobby().move("v001", options, actions, seat, [])
    if not first.plan:
        pytest.skip("this bundle is a single move")
    after = [*actions, first.action]
    second = lobby().move("v001", options, after, seat, first.plan) if to_act(replay(options, after)[0]) == seat else None
    if second is not None:
        assert not second.searched and second.action == first.plan[0] and second.plan == first.plan[1:]


def test_a_plan_that_does_not_fit_the_game_is_replaced_by_a_search() -> None:
    options, actions = a_game(13, 40)
    state, _, _ = replay(options, actions)
    seat = to_act(state)
    assert seat is not None
    reply = lobby().move("v001", options, actions, seat, [{"type": "no_such_move"}])
    assert reply.searched and reply.action in engine.legal_moves(state)


def test_the_same_request_gives_the_same_move() -> None:
    options, actions = a_game(14, 60)
    state, _, _ = replay(options, actions)
    seat = to_act(state)
    assert seat is not None
    a = lobby().move("v001", options, actions, seat, [])
    b = lobby().move("v001", options, actions, seat, [])
    assert (a.action, a.plan) == (b.action, b.plan), "a retry after a failure plays the same move"


def test_another_seat_or_another_model_is_refused() -> None:
    options, actions = a_game(15, 30)
    state, _, _ = replay(options, actions)
    seat = to_act(state)
    assert seat is not None
    with pytest.raises(NotYourTurn):
        lobby().move("v001", options, actions, 1 - seat, [])
    with pytest.raises(NoSuchModel):
        lobby().move("v999", options, actions, seat, [])


def test_the_model_plays_a_whole_game_through_requests_like_the_worker_makes_them() -> None:
    """The seat of the model asks for each move with the whole log; the other seat is a bot. The game ends and every move was legal."""
    options = Options(players=2, seed=21)
    other = bots.heuristic()
    actions: list[dict] = []  # type: ignore[type-arg]
    plan: list[dict] = []  # type: ignore[type-arg]
    rng = random.Random(0)
    lob = lobby()
    asks = 0
    while True:
        state, _, _ = replay(options, actions)
        seat = to_act(state)
        if seat is None:
            break
        if seat == 0:
            reply = lob.move("v001", options, actions, 0, plan)
            move, plan = reply.action, reply.plan
            asks += 1
        else:
            from seti_engine.projection import project

            view = project(state, seat, previews=False)
            move = view.legal[other.act(state, view, rng)]
        assert move in engine.legal_moves(state)
        actions.append(move)
        assert len(actions) < 3000
    assert asks > 20


def test_only_the_approved_versions_are_served(tmp_path: Path) -> None:
    (tmp_path / "index.json").write_text(json.dumps([{"version": "v001", "approved": False}, {"version": "v002", "approved": True}]), encoding="utf-8")
    assert approved_versions(tmp_path) == ["v002"]
    assert approved_versions(tmp_path, allow_unapproved=True) == ["v001", "v002"]
    assert approved_versions(tmp_path / "nothing") == []


def test_the_service_answers_a_signed_free_request_with_a_move(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    pytest.importorskip("cryptography")
    from fastapi.testclient import TestClient

    from seti_ai import lobby_server

    monkeypatch.delenv("ENGINE_TRUSTED_KEYS", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.setattr(lobby_server, "_lobby", lobby())
    options, actions = a_game(31, 30)
    state, _, _ = replay(options, actions)
    seat = to_act(state)
    client = TestClient(lobby_server.app)
    ok = client.post("/move", json={"model": "v001", "options": options.model_dump(), "actions": actions, "seat": seat, "plan": []})
    assert ok.status_code == 200 and ok.json()["action"] in engine.legal_moves(state)
    assert client.post("/move", json={"model": "v9", "options": options.model_dump(), "actions": actions, "seat": seat}).status_code == 404
    assert client.post("/move", json={"model": "v001", "options": options.model_dump(), "actions": actions, "seat": 1 - seat}).status_code == 409
    assert client.get("/models").json() == {"models": ["v001"]}
    assert client.get("/health").status_code == 200


def test_the_export_copies_only_the_approved_versions(tmp_path: Path) -> None:
    from seti_ai.lobby_export import export

    src = tmp_path / "models"
    for v in ("v001", "v002"):
        (src / v).mkdir(parents=True)
        (src / v / "model.pt").write_bytes(b"w")
        (src / v / "manifest.json").write_text("{}", encoding="utf-8")
    (src / "index.json").write_text(json.dumps([{"version": "v001", "approved": False}, {"version": "v002", "approved": True}]), encoding="utf-8")
    assert export(src, tmp_path / "out") == ["v002"]
    assert (tmp_path / "out" / "v002" / "model.pt").exists() and not (tmp_path / "out" / "v001").exists()


def test_approving_a_version_is_written_where_the_export_reads_it(tmp_path: Path) -> None:
    from seti_ai.lobby_export import export
    from seti_ai.publish import mark_approved

    (tmp_path / "v001").mkdir()
    (tmp_path / "v001" / "model.pt").write_bytes(b"w")
    (tmp_path / "v001" / "manifest.json").write_text(json.dumps({"version": "v001", "approved": False}), encoding="utf-8")
    (tmp_path / "index.json").write_text(json.dumps([{"version": "v001", "approved": False}]), encoding="utf-8")
    assert approved_versions(tmp_path) == []
    mark_approved(tmp_path, ["v001"])
    assert approved_versions(tmp_path) == ["v001"]
    assert json.loads((tmp_path / "v001" / "manifest.json").read_text(encoding="utf-8"))["approved"] is True
    assert export(tmp_path, tmp_path / "out") == ["v001"]
