"""Solo objectives: the stack, the three revealed tiles, task marking, completion and the end-of-round check against the rival.

Spec: solo.md (SOLO-OBJ-01 to SOLO-OBJ-08), board-solo-and-scoring.md (SOLO-DATA-13, SOLO-DATA-20), faq.md (FAQ-32).
"""

from __future__ import annotations

from typing import Any

from . import rng, tables
from .models import Decision, GameState, ObjectiveState, PlayerState

Events = list[dict[str, Any]]
LEVELS = ("I", "II", "III")
PENALTY_PROGRESS = 3  # SOLO-OBJ-06
UNDONE_POINTS = 5  # SOLO-OBJ-07


def tile(obj_id: str) -> dict[str, Any]:
    for o in tables.objectives()["objectives"]:
        if o["id"] == obj_id:
            found: dict[str, Any] = o
            return found
    raise KeyError(obj_id)


def setup(s: GameState, difficulty: int) -> None:
    """SOLO-OBJ-01 to SOLO-OBJ-03: shuffle each level, take the numbers of the rival's board, stack III, II, I, reveal the top 3."""
    if difficulty == 1:  # SOLO-OBJ-08: no objectives on 1 star
        return
    counts = next(b["objectives"][str(difficulty)] for b in tables.solo_boards()["boards"] if difficulty in b["stars"])
    stack: list[str] = []
    for level in reversed(LEVELS):  # level III at the bottom, level I on top
        ids = [o["id"] for o in tables.objectives()["objectives"] if o["level"] == level]
        stack += rng.shuffled(s, ids)[: counts[level]]
    s.objectives = ObjectiveState(stack=stack)
    for _ in range(3):
        reveal(s)


def reveal(s: GameState) -> None:
    ob = s.objectives
    assert ob is not None
    if not ob.stack:
        return
    oid = ob.stack.pop()
    ob.row.append(oid)
    ob.marks[oid] = [False] * len(tile(oid)["tasks"])


def human(s: GameState) -> PlayerState:
    assert s.rival is not None
    return next(p for p in s.players if p.index != s.rival.index)


# ---------------------------------------------------------------------------------------------------------------------------------
# marking tasks
# ---------------------------------------------------------------------------------------------------------------------------------


def _threshold(alt: dict[str, Any], p: PlayerState) -> bool:
    k = alt["kind"]
    n: int = alt.get("n", 0)
    if k == "reach_vp":
        return p.score >= n
    if k == "data_in_pool":
        return p.data_pool >= n  # data on the computer does not count
    if k == "reach_publicity":
        return p.publicity >= n
    return False


def check_thresholds(s: GameState) -> None:
    """Tasks about reaching a level are marked as soon as it is reached, or at once if it already is (SOLO-OBJ-04)."""
    ob = s.objectives
    if ob is None:
        return
    p = human(s)
    for oid in ob.row:
        for i, task in enumerate(tile(oid)["tasks"]):
            if not ob.marks[oid][i] and any(_threshold(alt, p) for alt in task):
                ob.marks[oid][i] = True


def _matches(alt: dict[str, Any], ev: dict[str, Any]) -> bool:
    k, e = alt["kind"], ev["e"]
    if k == "action":
        return bool(alt["action"] == e)
    if k == "win_sector":
        return bool(e == "win_sector" and ("any" in alt["sectors"] or ev["color"] in alt["sectors"]))
    if k == "tech":
        return bool(e == "tech" and alt["type"] in ("any", ev["cat"]))
    if k == "orbit_or_land":
        return bool(e in ("orbit", "land") and ev.get("planet") == alt["planet"])
    if k == "life_trace":
        return bool(e == "trace" and ev.get("kind") == alt["color"])
    if k == "visit":
        return bool(e == ("visit_asteroids" if alt["what"] == "asteroids" else "visit_comet"))
    if k == "complete_mission":
        return bool(e == "mission_done")
    if k == "play_card_costing":
        return bool(e == "play_cost" and ev.get("cost") == alt["credits"])
    return False


def candidates(s: GameState, evs: list[dict[str, Any]]) -> list[list[Any]]:
    ob = s.objectives
    out: list[list[Any]] = []
    if ob is None:
        return out
    for oid in ob.row:
        for i, task in enumerate(tile(oid)["tasks"]):
            if not ob.marks[oid][i] and any(_matches(alt, ev) for alt in task for ev in evs):
                out.append([oid, i])
    return out


def on_event(s: GameState, p: PlayerState, evs: list[dict[str, Any]]) -> None:
    """A trigger can mark only one task, even across objectives; with several possible the player chooses (SOLO-OBJ-04)."""
    if s.objectives is None or s.rival is None or p.index == s.rival.index:
        return
    cands = candidates(s, evs)
    if len(cands) == 1:
        s.objectives.marks[cands[0][0]][cands[0][1]] = True
    elif cands:
        s.pending.insert(0, Decision(kind="objective_task", player=p.index, data={"options": cands}))


def mark(s: GameState, oid: str, i: int) -> None:
    assert s.objectives is not None
    s.objectives.marks[oid][i] = True


def completed(s: GameState) -> list[str]:
    ob = s.objectives
    assert ob is not None
    return [oid for oid in ob.row if all(ob.marks[oid])]


# ---------------------------------------------------------------------------------------------------------------------------------
# turn and round ends
# ---------------------------------------------------------------------------------------------------------------------------------


def end_turn(s: GameState) -> None:
    """SOLO-OBJ-05: completed objectives go to the pile and are replaced from the stack, so there are three while the stack lasts."""
    ob = s.objectives
    if ob is None:
        return
    for oid in completed(s):
        ob.row.remove(oid)
        ob.pile.append(oid)
    while len(ob.row) < 3 and ob.stack:
        reveal(s)
    check_thresholds(s)


def end_round(s: GameState, rnd: int, events: Events) -> None:
    """SOLO-OBJ-06, SOLO-OBJ-07: after rounds 1 to 4 spend as many completed objectives as the round number, the rival advances 3 for
    each it cannot; after round 5 the rival scores 5 points for each uncompleted objective (rival.py applies the effects)."""
    from . import rival  # noqa: PLC0415

    ob = s.objectives
    if ob is None:
        return
    if rnd <= 4:
        spent = min(rnd, len(ob.pile))
        del ob.pile[:spent]
        short = rnd - spent
        events.append({"type": "objectives_spent", "round": rnd, "spent": spent, "short": short})
        if short:
            rival.advance(s, PENALTY_PROGRESS * short, events)
    else:
        undone = len([o for o in ob.row if not all(ob.marks[o])]) + len(ob.stack)
        events.append({"type": "objectives_uncompleted", "count": undone})
        rival.gain_vp(s, UNDONE_POINTS * undone, events)
