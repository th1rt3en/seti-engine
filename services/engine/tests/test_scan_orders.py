"""The steps of a scan in any order (SCAN-01, owner ruling 2026-10-22), for every combination of the four pink (telescope) techs and 0, 1
or 2 signal tokens.

For each of the 16 sets of telescope techs and each number of signal tokens, the scan is played through in many orders of its steps (all
the orders when there are few, a fixed sample otherwise, always the order of the board and its reverse). At every state of every path the
moves that the engine offers are checked:
- the scan can only be finished once the signal in Earth's sector and the card of the row are done (SCAN-02, SCAN-03);
- a step that was done is not offered again, a signal token is used once each, and the techs once each (SCAN-04);
- every step that can be done is offered while it is left, whatever was done before it (SCAN-01);
- the scan never dead-ends, and when it is finished the row is full again and no scan step is left (SCAN-03, FAQ-15);
- the signals that were marked add up to the steps that were done (SCAN-05).
The games played from left to right (a `scan_skip` in the log, TECH-TT03/TT02/TT04) still replay."""

import itertools
import random
from typing import Any

import pytest
from test_engine import begin, do, with_state

from seti_engine import solar
from seti_engine.engine import StepResult, apply, legal_moves
from seti_engine.models import GameState

TECHS = ("telescope-dot", "telescope-link", "telescope-branch", "telescope-cross")
SCAN_TYPES = {"scan_earth", "scan_discard", "scan_token", "scan_hand_discard", "scan_mercury", "scan_probe", "scan_done"}
SAMPLE = 8  # orders tried when there are too many to try them all


def scan_started(techs: tuple[str, ...], tokens: int) -> StepResult:
    r = begin(2)
    s = r.state.model_copy(deep=True)
    p = s.players[s.current_player]
    p.credits, p.energy, p.publicity, p.signal_tokens = 3, 6, 5, tokens
    p.techs += techs
    return do(with_state(s), "scan")


def key_of(m: dict[str, Any]) -> str:
    """The step that a scan move belongs to."""
    t = m["type"]
    return {
        "scan_earth": "earth",
        "scan_discard": "row",
        "scan_token": "token",
        "scan_hand_discard": "hand",
        "scan_mercury": "mercury",
        "scan_probe": f"probe-{m.get('mode')}",
        "scan_done": "done",
    }[t]


def steps_of(techs: tuple[str, ...], tokens: int, mode: str) -> list[str]:
    out = ["earth", "row", *["token"] * tokens]
    if "telescope-link" in techs:
        out.append("mercury")
    if "telescope-branch" in techs:
        out.append("hand")
    if "telescope-cross" in techs:
        out.append(f"probe-{mode}")
    return out


def orders(steps: list[str], seed: int) -> list[list[str]]:
    distinct = sorted(set(itertools.permutations(steps)))
    if len(distinct) <= 24:
        return [list(o) for o in distinct]
    rnd = random.Random(seed)
    chosen = [list(steps), list(reversed(steps))]
    while len(chosen) < SAMPLE + 2:
        o = list(steps)
        rnd.shuffle(o)
        if o not in chosen:
            chosen.append(o)
    return chosen


def settle(r: StepResult, events: list[dict[str, Any]]) -> StepResult:
    """Answer the decisions that are not a step of the scan (the choice of a sector for a signal, a reward)."""
    while r.state.pending and r.state.pending[0].kind != "scan_step":
        r = apply(r.state, r.legal[0])
        events += r.events
    return r


def play_order(
    r: StepResult, order: list[str], techs: tuple[str, ...], tokens: int, variant: int
) -> tuple[StepResult, list[dict[str, Any]]]:
    """Play the scan taking the steps in `order` (the first of them that is offered at each point), checking what is offered at every state."""
    pl = r.state.current_player
    start = r.state
    events: list[dict[str, Any]] = list(r.events)
    done: list[str] = []
    tokens_left = tokens
    r = settle(r, events)
    for _ in range(40):
        offered = [m for m in r.legal if m["type"] in SCAN_TYPES]
        kinds = [key_of(m) for m in offered]
        p = r.state.players[pl]
        # SCAN-02, SCAN-03: the scan can be finished once Earth's sector and the card of the row are done, and not before
        main_done = "earth" in done and "row" in done
        assert ("done" in kinds) == main_done, (done, kinds)
        # a step that was done is not offered again; the tokens are used one each
        for once in ("earth", "row", "mercury", "hand"):
            if once in done:
                assert once not in kinds, (once, done)
        if "probe-launch" in done or "probe-move" in done:
            assert not any(k.startswith("probe") for k in kinds), done
        assert p.signal_tokens == tokens_left
        if tokens_left == 0:
            assert "token" not in kinds
        # SCAN-01: a step that can be done is offered whatever was done before it (the row and the tokens need a card in the row)
        if "earth" not in done:
            assert "earth" in kinds
        if "row" not in done:
            assert "row" in kinds
        if "mercury" not in done and "telescope-link" in techs and p.publicity >= 1:
            assert "mercury" in kinds
        if "hand" not in done and "telescope-branch" in techs and any(c for c in p.hand):
            assert "hand" in kinds or not [c for c in p.hand if _has_sector(c)]
        if "telescope-cross" in techs and not any(d.startswith("probe") for d in done):
            assert "probe-move" in kinds, "the free movement is always possible"
        if tokens_left > 0 and r.state.card_row:
            assert "token" in kinds
        # take the next step of the order that is offered; when none is, finish the scan
        nxt = next((k for k in order if k in kinds and not _taken(k, done, order)), None)
        if nxt is None:
            assert "done" in kinds, ("the scan has no way on", done, kinds)
            nxt = "done"
        moves = [m for m in offered if key_of(m) == nxt]
        move = moves[variant % len(moves)]
        if nxt == "token":
            tokens_left -= 1
        done.append(nxt)
        r = apply(r.state, move)
        events += r.events
        r = settle(r, events)
        if nxt == "done":
            break
    else:
        pytest.fail(f"the scan did not end: {done}")
    # when the scan is finished (SCAN-03, FAQ-15)
    assert r.state.scan_steps == [] and not any(d.kind == "scan_step" for d in r.state.pending)
    assert len(r.state.card_row) == 3, "the row is refilled after the whole scan"
    # SCAN-05: the signals that were marked add up to the steps that were done
    marked = sum(1 for e in events if e["type"] == "signal" and e["player"] == pl)
    expected = sum(1 for d in done if d in ("earth", "row", "token", "mercury", "hand"))
    assert marked == expected, (marked, expected, done)
    assert r.state.players[pl].signal_tokens == tokens_left
    assert r.state.players[pl].energy >= 0 and r.state.players[pl].publicity >= 0
    # the cost of the scan itself and of the paid steps was taken once
    launched = "probe-launch" in done
    assert len([x for x in r.state.probes if x.player == pl]) - len([x for x in start.probes if x.player == pl]) == (1 if launched else 0)
    return r, done  # type: ignore[return-value]


def _has_sector(card: str) -> bool:
    from seti_engine import tables

    return bool(tables.cards()[card].get("sector"))


def _taken(kind: str, done: list[str], order: list[str]) -> bool:
    """A step of the order that was done already (the tokens are several steps of the same kind)."""
    return done.count(kind) >= order.count(kind)


COMBOS = [(techs, tokens) for n in range(5) for techs in itertools.combinations(TECHS, n) for tokens in (0, 1, 2)]


@pytest.mark.parametrize(
    ("techs", "tokens"), COMBOS, ids=[f"{'+'.join(t.split('-')[1] for t in c[0]) or 'no-tech'}-{c[1]}-tokens" for c in COMBOS]
)
def test_every_order_of_the_steps_of_a_scan_works(
    techs: tuple[str, ...], tokens: int
) -> None:  # SCAN-01 to SCAN-05, TECH-TT01 to TECH-TT04, EXP-SIG-02
    base = scan_started(techs, tokens)
    for mode in ("move", "launch") if "telescope-cross" in techs else ("move",):
        for i, order in enumerate(orders(steps_of(techs, tokens, mode), seed=len(techs) * 10 + tokens)):
            play_order(base, order, techs, tokens, variant=i)


def test_the_scan_can_be_finished_at_once_when_only_the_two_main_steps_are_done_whatever_techs_and_tokens_are_left() -> None:  # SCAN-04
    for techs, tokens in COMBOS:
        r = scan_started(techs, tokens)
        events: list[dict[str, Any]] = []
        pl = r.state.current_player
        r = apply(r.state, next(m for m in r.legal if m["type"] == "scan_discard"))
        r = settle(r, events)
        r = apply(r.state, next(m for m in r.legal if m["type"] == "scan_earth"))
        r = settle(r, events)
        assert any(m["type"] == "scan_done" for m in r.legal), (techs, tokens)
        r = apply(r.state, {"type": "scan_done"})
        assert r.state.players[pl].signal_tokens == tokens and len(r.state.card_row) == 3


@pytest.mark.parametrize("tokens", [0, 1, 2])
def test_a_token_can_be_spent_before_the_card_of_the_row_and_the_row_step_still_has_a_card(tokens: int) -> None:  # EXP-SIG-02
    r = scan_started((), tokens)
    for _ in range(tokens):
        r = settle(apply(r.state, next(m for m in r.legal if m["type"] == "scan_token")), [])
    assert any(m["type"] == "scan_discard" for m in r.legal), (
        "the card of the row is still possible after two tokens (the row has three cards)"
    )
    assert len(r.state.card_row) == 3 - tokens


def test_a_signal_token_and_a_tech_step_before_earth_end_with_the_same_signals_as_the_board_order() -> None:  # SCAN-01
    techs = ("telescope-link", "telescope-branch")
    base = scan_started(techs, 1)
    _, first = play_order(base, ["token", "mercury", "hand", "row", "earth"], techs, 1, 0)
    _, second = play_order(base, ["earth", "row", "token", "mercury", "hand"], techs, 1, 0)
    assert sorted(first) == sorted(second)


@pytest.mark.parametrize(
    ("techs", "tokens"), COMBOS, ids=[f"{'+'.join(t.split('-')[1] for t in c[0]) or 'no-tech'}-{c[1]}-tokens" for c in COMBOS]
)
def test_a_game_played_from_left_to_right_with_scan_skip_still_replays(techs: tuple[str, ...], tokens: int) -> None:  # SCAN-01
    """The old log: Earth's sector, the card of the row, the tokens, then each tech or a `scan_skip`, then `scan_done`."""
    for skip_techs in (False, True):
        r = scan_started(techs, tokens)
        events: list[dict[str, Any]] = []
        for want in ("scan_earth", "scan_discard"):
            r = settle(apply(r.state, next(m for m in r.legal if m["type"] == want)), events)
        for _ in range(tokens):
            r = settle(apply(r.state, next(m for m in r.legal if m["type"] == "scan_token")), events)
        guard = 0
        while guard < 10:
            guard += 1
            doable = [m for m in r.legal if m["type"] in ("scan_mercury", "scan_hand_discard", "scan_probe")]
            if not doable:
                break
            if skip_techs:
                r = apply(r.state, {"type": "scan_skip"})  # the old move: the current optional step is not done
            else:
                r = settle(apply(r.state, doable[0]), events)
        assert any(m["type"] == "scan_done" for m in r.legal)
        r = apply(r.state, {"type": "scan_done"})
        assert r.state.scan_steps == [] and len(r.state.card_row) == 3


def test_the_moves_of_the_scan_are_all_legal_moves_of_the_engine() -> None:  # SCAN-01: what is offered can be played
    r = scan_started(TECHS, 2)
    for m in [m for m in r.legal if m["type"] in SCAN_TYPES]:
        assert m in legal_moves(r.state)
        apply(r.state, m)  # no move that is offered is refused


def test_earth_sector_choices_of_the_dot_tech_are_offered_before_other_steps() -> None:  # TECH-TT01, SCAN-01
    r = scan_started(("telescope-dot",), 0)
    e = solar.earth(r.state)[1]
    assert {m["sector"] for m in r.legal if m["type"] == "scan_earth"} == {e, (e - 1) % 8, (e + 1) % 8}


def _unused(_: GameState) -> None:  # keeps the import of GameState for the annotations above
    return None
