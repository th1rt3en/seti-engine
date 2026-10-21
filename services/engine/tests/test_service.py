"""The projection of hidden information and the HTTP service (CLAUDE.md rule 6, decision D11)."""

from fastapi.testclient import TestClient

from seti_engine import projection, protocol
from seti_engine.engine import StepResult, apply, legal_moves, start
from seti_engine.models import GameState, Options
from seti_engine.service import app

client = TestClient(app)


def game(players: int = 3, seed: int = 4) -> GameState:
    r = start(Options(players=players, seed=seed))
    while r.state.pending:
        r = apply(r.state, r.legal[0])
    return r.state


def test_a_player_sees_their_own_hand_and_only_the_size_of_the_others() -> None:
    s = game()
    v = projection.project(s, 1)
    assert v.state.players[1].hand == s.players[1].hand
    assert v.state.players[0].hand == ["?"] * len(s.players[0].hand) and v.counts.hands == [len(p.hand) for p in s.players]
    spectator = projection.project(s, None)
    assert all(set(p.hand) <= {"?"} for p in spectator.state.players)


def test_the_deck_the_stacks_the_tiles_and_the_generator_are_hidden() -> None:
    s = game()
    v = projection.project(s, 0)
    assert set(v.state.deck) == {"?"} and v.counts.deck == len(s.deck)
    assert all(set(x) == {"?"} for x in v.state.end_of_round_stacks) and v.counts.end_of_round_stacks == [
        len(x) for x in s.end_of_round_stacks
    ]
    # SETUP-16: the top tile of a stack lies bonus side up, the tiles under it are hidden
    assert all(set(t.tiles[1:]) <= {"?"} and t.tiles[0] == s.tech_stacks[i].tiles[0] for i, t in enumerate(v.state.tech_stacks))
    assert v.state.rng_state == 0
    assert [t.two_point_tile for t in v.state.tech_stacks] == [t.two_point_tile for t in s.tech_stacks]


def test_species_stay_hidden_until_discovered() -> None:
    s = game()
    assert [x.species for x in projection.project(s, 0).state.species] == ["?", "?"]
    s.species[0].discovered = True
    shown = projection.project(s, 0).state.species
    assert shown[0].species == s.species[0].species and shown[1].species == "?"


def test_only_the_player_to_act_gets_the_legal_moves_and_the_decision_data() -> None:
    r = start(Options(players=2, seed=1))
    actor = r.state.pending[0].player
    other = 1 - actor
    assert projection.project(r.state, actor).legal == r.legal and projection.project(r.state, other).legal == []
    assert projection.project(r.state, other).state.pending[0].data == {} and projection.project(r.state, None).legal == []
    assert projection.project(r.state, other).to_act == actor


def test_exertian_cards_and_the_solo_decks_are_hidden() -> None:
    s = game(2)
    s.players[0].exertian_hand = ["ET.41", "ET.42"]
    s.players[0].exertian_played = ["ET.43"]
    assert projection.project(s, 0).state.players[0].exertian_hand == ["ET.41", "ET.42"]
    other = projection.project(s, 1)
    assert other.state.players[0].exertian_hand == ["?", "?"] and other.state.players[0].exertian_played == ["?"]
    solo = start(Options(players=1, seed=2, difficulty=3)).state
    v = projection.project(solo, 0)
    assert set(v.state.rival.deck) == {"?"} and set(v.state.rival.advanced) == {"?"} and v.counts.rival_deck == len(solo.rival.deck)  # type: ignore[union-attr]
    assert set(v.state.objectives.stack) == {"?"} and v.state.objectives.row == solo.objectives.row  # type: ignore[union-attr]


def test_the_projection_of_a_state_does_not_change_it() -> None:
    s = game()
    before = s.model_dump()
    projection.project(s, 0)
    assert s.model_dump() == before


# --- the service -----------------------------------------------------------------------------------------------------------------


def test_health_and_schema() -> None:
    assert client.get("/health").json() == {"status": "ok", "protocol": protocol.PROTOCOL_VERSION}
    body = client.get("/schema").json()
    assert body["protocol"] == protocol.PROTOCOL_VERSION and set(body["schemas"]) == set(protocol.MODELS)


def test_a_whole_game_through_the_service_matches_the_engine() -> None:
    res = client.post("/new", json={"options": {"players": 2, "seed": 9}})
    assert res.status_code == 200
    state, legal = res.json()["state"], res.json()["legal"]
    local = start(Options(players=2, seed=9))
    for _ in range(40):
        if not legal:
            break
        move = legal[len(legal) // 2]
        res = client.post("/apply", json={"state": state, "action": move})
        assert res.status_code == 200
        local = apply(local.state, move)
        body = res.json()
        assert body["state"] == local.state.model_dump(mode="json") and body["legal"] == local.legal
        state, legal = body["state"], body["legal"]


def test_an_illegal_action_is_refused_with_the_legal_moves() -> None:
    r: StepResult = start(Options(players=2, seed=1))
    res = client.post("/apply", json={"state": r.state.model_dump(mode="json"), "action": {"type": "launch"}})
    assert res.status_code == 422 and res.json()["error"] == "illegal_action" and res.json()["legal"] == r.legal


def test_legal_and_project_endpoints() -> None:
    r = start(Options(players=2, seed=1))
    st = r.state.model_dump(mode="json")
    assert client.post("/legal", json={"state": st}).json()["legal"] == legal_moves(r.state)
    actor = r.state.pending[0].player
    v = client.post("/project", json={"state": st, "viewer": actor}).json()
    assert v["viewer"] == actor and v["legal"] == r.legal and v["to_act"] == actor and v["state"]["rng_state"] == "0"
    assert client.post("/project", json={"state": st, "viewer": None}).json()["legal"] == []


def test_the_service_keeps_no_state_between_requests() -> None:
    first = client.post("/new", json={"options": {"players": 1, "seed": 3, "difficulty": 2}}).json()
    again = client.post("/new", json={"options": {"players": 1, "seed": 3, "difficulty": 2}}).json()
    assert first == again


def test_the_committed_protocol_schema_is_up_to_date() -> None:
    """D11: packages/protocol/schema/protocol.schema.json is generated from the models; regenerate it with tools/engine/gen_protocol.py."""
    import importlib.util
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("gen_protocol", root / "tools" / "engine" / "gen_protocol.py")
    assert spec is not None and spec.loader is not None
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    committed = (root / "packages" / "protocol" / "schema" / "protocol.schema.json").read_text(encoding="utf-8")
    assert committed == gen.render(), (
        "the protocol schema is out of date: run tools/engine/gen_protocol.py and pnpm --filter @seti/protocol generate"
    )
