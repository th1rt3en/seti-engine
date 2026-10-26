"""The trail of gains: who gained or lost what, and because of what, for the log.

A scope names the cause of everything that changes inside it (a card, a sector, a mission, a milestone ...). When the scope ends,
the change of each player's points and resources between its start and its end, less what scopes inside it have already accounted
for, is recorded under its name. Decisions that are put to a player inside the scope are named after it too (`Decision.source`).
The records are turned into `gains` events at the end of the step (engine._step). Nothing here changes a rule: it only watches the numbers.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .models import GameState

KINDS = ("vp", "credit", "energy", "publicity", "data", "card", "move")


def _snapshot(s: GameState) -> list[dict[str, int]]:
    return [
        {
            "vp": p.score,
            "credit": p.credits,
            "energy": p.energy,
            "publicity": p.publicity,
            "data": p.data_pool,
            "card": len(p.hand),
            "move": p.movement,
        }
        for p in s.players
    ]


@contextmanager
def scope(s: GameState, source: dict[str, Any], turn: str | None = None) -> Iterator[None]:
    """What the players gain or lose inside the block, that no scope inside it claimed, is recorded for `source`.
    `turn` names the rival's turn (its action card) that everything inside belongs to, so that the log can show each turn on its own."""
    start = len(s.trail)
    before = _snapshot(s)
    known = list(s.pending)  # held, so that no id is reused
    yield
    for d in s.pending:  # a decision this block caused is named after the innermost scope that was open when it was made
        if d.source is None and not any(d is k for k in known):
            d.source = source
    for rec in s.trail[start:]:  # a gain that did not fit is named after the innermost scope it happened in
        if "lost" in rec and "source" not in rec:
            rec["source"] = source
    after = _snapshot(s)
    claimed: list[dict[str, int]] = [dict.fromkeys(KINDS, 0) for _ in s.players]
    for rec in s.trail[start:]:
        for k, v in rec["changes"].items():
            claimed[rec["player"]][k] += v
    for i, (b, a) in enumerate(zip(before, after, strict=True)):
        changes = {k: a[k] - b[k] - claimed[i][k] for k in KINDS}
        changes = {k: v for k, v in changes.items() if v != 0}
        if changes:
            s.trail.append({"player": i, "source": source, "changes": changes})
    if turn is not None:
        for rec in s.trail[start:]:
            rec.setdefault("turn", turn)


def cost(s: GameState, what: str) -> Any:
    """What a player pays or gives up inside the block (a cost, a card that leaves the hand, data that goes to the computer)
    is recorded apart as `{"kind": "cost", "what": ...}`: it does not cancel what the effect that follows gives.
    The statistics count it as what the resource was spent on."""
    return scope(s, {"kind": "cost", "what": what})


def events_of(s: GameState) -> list[dict[str, Any]]:
    """The `gains` events of a step: one for each source and player, in the order each first gained something. The trail is emptied."""
    out: list[dict[str, Any]] = []
    index: dict[tuple[int, str], int] = {}
    for rec in s.trail:
        if "lost" in rec:  # a gain that did not fit (RES-01, RES-02): "can't gain 2 publicity, already at the maximum"
            for kind, n in rec["lost"].items():
                ev: dict[str, Any] = {"type": "capped", "player": rec["player"], "kind": kind, "n": n}
                if rec.get("source") is not None:
                    ev["source"] = rec["source"]
                out.append(ev)
            continue
        if rec.get("grows"):  # SOLO-12: the rival crossed the growth icon and put an advanced action card on top of its deck
            out.append({"type": "rival_grows", "player": rec["player"]})
            continue
        if "draw" in rec:  # a card drawn from the deck: the log names it for the player who drew it (the others are not told which)
            out.append({"type": "draw_card", "player": rec["player"], "card": rec["draw"], "changes": {}})
            continue
        key = (rec["player"], repr(sorted(rec["source"].items())) + str(rec.get("turn")))
        if key in index:
            merged = out[index[key]]["changes"]
            for k, v in rec["changes"].items():
                merged[k] = merged.get(k, 0) + v
        else:
            index[key] = len(out)
            out.append({"type": "gains", "player": rec["player"], "source": rec["source"], "changes": dict(rec["changes"])})
            if "turn" in rec:
                out[-1]["turn"] = rec["turn"]
    s.trail = []
    kept = [e for e in out if e["type"] in ("draw_card", "capped", "rival_grows") or any(v != 0 for v in e["changes"].values())]
    return [{k: v for k, v in e.items() if k != "changes"} if e["type"] == "draw_card" else e for e in kept]
