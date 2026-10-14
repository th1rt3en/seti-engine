"""Final scoring: end-of-game cards, gold scoring tiles, and the Exertian danger step.

Spec: milestones-and-scoring.md (END-01 to END-03, END-10 to END-17, MILE-02, MILE-03), cards-and-missions.md (CARD-20, CARD-21),
faq.md (FAQ-34, FAQ-C113, FAQ-C231), aliens.md (ALIEN-EXE-06, ALIEN-EXE-07).
"""

from __future__ import annotations

from typing import Any

from . import cards, species, tables
from .models import GameState, GoldTile, PlayerState

TECH_CATEGORIES = ("probe", "telescope", "computer")


def tile_values(g: GoldTile) -> list[int]:
    """Points per set under the first, second and third (or later) marker of the tile (MILE-03)."""
    for t in tables.gold_tiles()["tiles"]:
        if t["tile"] == g.tile and t["side"] == g.side:
            values: list[int] = t["values"]
            return values
    raise KeyError((g.tile, g.side))


def sector_wins(s: GameState, p: PlayerState) -> int:
    """SECTOR-20, END-17: every marker beside a star counts, even several in the same sector."""
    return sum(sec.winners.count(p.index) for sec in s.sectors)


def sets_for(s: GameState, p: PlayerState, g: GoldTile) -> int:
    """How many times the tile's condition is met by the player (END-10 to END-17)."""
    if g.tile == "Tech":
        counts = [sum(1 for t in p.techs if t.startswith(c + "-")) for c in TECH_CATEGORIES]
        return min(counts) if g.side == "A" else sum(counts) // 2  # END-10, END-11
    if g.tile == "Mission":
        done = len(p.completed_missions)
        return done if g.side == "A" else (done + len(p.end_cards)) // 2  # END-12, END-13; FAQ-34: end cards scoring 0 still count
    if g.tile == "Income":
        income = [tables.cards()[c]["income"] for c in p.tucked]  # the starting income card is not counted (END-14)
        credit, energy, card = (income.count(k) for k in ("credit", "energy", "card"))  # FAQ-C231: publicity and data do not count
        return min(credit, energy, card) if g.side == "A" else max(credit, energy)  # END-14, END-15
    return (
        _other_sets(s, p) if g.side == "A" else min(sector_wins(s, p), sum(p.orbiters.values()) + sum(p.landers.values()))
    )  # END-16, END-17


def _other_sets(s: GameState, p: PlayerState) -> int:
    """END-16: sets of three life traces, one of each color. Markers on overflow spaces count by the color of their space (A-022)."""
    return min(sum(1 for _, k in p.trace_log if k == c) for c in ("pink", "yellow", "blue"))


def gold_points(s: GameState, p: PlayerState) -> int:
    total = 0
    for g in s.gold_tiles:
        if p.index in g.markers:
            total += tile_values(g)[min(g.markers.index(p.index), 2)] * sets_for(s, p, g)
    return total


def solvay_points(s: GameState, p: PlayerState) -> int:
    """#113 Solvay Conference, FAQ-C113: the best tile the player did not mark, scored as if on its lowest (rightmost) value."""
    options = [tile_values(g)[2] * sets_for(s, p, g) for g in s.gold_tiles if p.index not in g.markers]
    return max(options, default=0)


def final_scores(s: GameState) -> list[dict[str, Any]]:
    """END-01 to END-03: the board score, the end-of-game cards, the gold tiles, the Exertian cards, then the Exertian danger loss."""
    rows: list[dict[str, Any]] = []
    for p in s.players:
        is_rival = s.rival is not None and p.index == s.rival.index
        cards_pts = cards.end_points(s, p)
        gold = 0 if is_rival else gold_points(s, p)  # the rival does not score gold tiles (SOLO-END-01)
        exertian = cards.exertian_points(s, p)
        rows.append({"player": p.index, "board": p.score, "cards": cards_pts, "gold": gold, "exertian": exertian, "loss": 0})
    totals = [r["board"] + r["cards"] + r["gold"] + r["exertian"] for r in rows]
    for r, loss in zip(rows, species.exertian_losses(s, totals), strict=True):  # ALIEN-EXE-07: after all other points
        r["loss"] = loss
        r["total"] = r["board"] + r["cards"] + r["gold"] + r["exertian"] - loss
        r["danger"] = species.danger(s, s.players[r["player"]])
    return rows


def winners(rows: list[dict[str, Any]], rival: int | None = None) -> list[int]:
    """END-01: the most points wins; equal scores tie. Solo: the player wins only with more points than the rival (SOLO-END-01)."""
    if rival is not None:
        mine = next(r for r in rows if r["player"] != rival)
        theirs = next(r for r in rows if r["player"] == rival)
        return [mine["player"]] if mine["total"] > theirs["total"] else [rival]
    best = max(r["total"] for r in rows)
    return [r["player"] for r in rows if r["total"] == best]
