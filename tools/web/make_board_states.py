"""Make the states of the alien boards for the review page (apps/web/src/app/demo/boards): for each species two board states,

- `prompts`: every place where a marker (or a token, an organelle ...) can be put at the same time, as the engine offers them (the moves and their notes);
- `markers`: markers of random players on every space, with several on the spaces that take more than one (a top capsule), the overflow spaces and the
  special places of the species (sample spaces, the 'Oumuamua tile, the Centaurian reward hexes, the glyph tokens and the translation board, the organelles).

The species go two to a board (the game has two species at a time): four pairs, two views each. Run from services/engine:
    python -m uv run python ../../tools/web/make_board_states.py
"""

import json
import pathlib
import random
from typing import Any

from seti_engine import amoeba, glyphids, species
from seti_engine.engine import start
from seti_engine.models import Decision, GameState, Options
from seti_engine.projection import project

OUT = pathlib.Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "generated" / "board-states.json"
PAIRS = [("anomalies", "centaurians"), ("exertians", "mascamites"), ("oumuamua", "arkhos"), ("glyphids", "amoeba")]
COLORS = ("pink", "yellow", "blue")
PLACES = ("place_trace", "choose_message", "signal_where", "decipher", "pick_organelle", "amoeba_remove")  # the moves that are a place on a board


def base_state(a: str, b: str, seed: int) -> GameState:
    """A game of 3 players in the middle of its first round with these two species discovered."""
    s = start(Options(players=3, seed=seed, expansion=True)).state.model_copy(deep=True)
    s.pending = []
    s.phase = "play"
    s.round = 2
    s.current_player = 0
    for i, name in enumerate((a, b)):
        slot = s.species[i]
        slot.species = name
        slot.board = species.new_board(name)
        slot.discovery_spaces = ["p0", "p1", "p2"]
        slot.deck, slot.extra = [], {}
        species._discover(s, i, [])
    me = s.players[0]
    me.data_pool, me.exofossils, me.credits, me.energy = 6, 6, 6, 6
    for p in s.players:
        p.hand = p.hand[:5]
    return s


def collect(state: GameState, decisions: list[Decision | None]) -> tuple[list[dict[str, Any]], list[Any]]:
    """The legal moves (with their notes) of the player of every decision, one after the other, without repeating a move."""
    legal: list[dict[str, Any]] = []
    notes: list[Any] = []
    seen: set[str] = set()
    for d in decisions:
        s = state.model_copy(deep=True)
        s.pending = [] if d is None else [d]
        v = project(s, 0, previews=False)
        for move, note in zip(v.legal, v.notes, strict=True):
            if move["type"] not in PLACES:
                continue
            key = json.dumps(move, sort_keys=True)
            if key not in seen:
                seen.add(key)
                legal.append(move)
                notes.append(note)
    return legal, notes


def prompts(s: GameState) -> tuple[GameState, list[dict[str, Any]], list[Any]]:
    names = [sl.species for sl in s.species]
    me = s.players[0]
    me.security = {}  # every security card breached: all the levels of Arkhos are open (EXP-ARK-05)
    for i, name in enumerate(names):
        if name == "mascamites":
            s.species[i].extra["sample_spaces"] = [species.new_sample_space(t) for t in range(7)]  # a sample space for each token
    decisions: list[Decision | None] = [Decision(kind="trace", player=0, data={"color": c}) for c in COLORS]
    if "oumuamua" in names:
        decisions.append(Decision(kind="oumuamua_signal", player=0, data={"sector": 0}))
    if "centaurians" in names:
        decisions.append(Decision(kind="message_reward", player=0))
    if "amoeba" in names:
        i = names.index("amoeba")
        for c in COLORS:
            decisions.append(Decision(kind="organelle", player=0, data={"color": c}))
        s.species[i].board = {c: [[1] for _ in col] for c, col in s.species[i].board.items()}  # something to remove, for `amoeba_remove`
        decisions.append(Decision(kind="amoeba_remove", player=0))
        s.species[i].board = species.new_board("amoeba")
        for c in COLORS:
            s.species[i].board[c][1] = [0]
        decisions.append(Decision(kind="amoeba_remove", player=0))
    if "glyphids" in names:
        me.glyphs = sorted(set(glyphids.data()["glyphs"]))
        decisions.append(None)  # the holes of the translation board are a free action
    legal, notes = collect(s, decisions)
    for i, name in enumerate(names):
        if name == "amoeba":
            s.species[i].board = species.new_board("amoeba")  # the markers that `amoeba_remove` needed are not part of the picture
    if "amoeba" in names:
        # the engine offers an organelle where there is one (five of the nine spaces); all nine are added to see where they lie
        have = {m["space"] for m in legal if m["type"] == "pick_organelle"}
        for sp in [x for ring in ("outer", "inner") for x, _ in amoeba.data()["rings"][ring]]:
            if sp not in have:
                legal.append({"type": "pick_organelle", "space": sp, "color": amoeba.color_of(sp)})
                notes.append(None)
    if "glyphids" in names:
        # the engine offers the holes of the top row only when the holes under them are filled; they are added here (as the page draws them) to see where they lie
        for g in sorted(set(glyphids.data()["glyphs"])):
            for k in range(3):
                legal.append({"type": "decipher", "glyph": g, "row": "top", "index": k})
                notes.append(None)
    return s, legal, notes


def markers(s: GameState, rnd: random.Random) -> GameState:
    """Markers of random players on every space, several where the space takes several."""
    for i, slot in enumerate(s.species):
        data = species.board_data(slot.species)
        for col in data["columns"]:
            color = col["color"]
            for k, space in enumerate(col["spaces"]):
                if not space["rewards"] and slot.species == "mascamites":
                    continue
                n = rnd.randint(2, 4) if space.get("repeat") else 1
                slot.board[color][k] = [rnd.randrange(3) for _ in range(n)]
        slot.overflow = [rnd.randrange(3) for _ in range(6)]
        slot.overflow_kinds = [COLORS[n % 3] for n in range(6)]
        if slot.species == "mascamites":
            slot.extra["sample_spaces"] = [
                {"token": t, "marker": rnd.randrange(3) if t % 2 == 0 else None, "reward": species.sample_faces()[t]} for t in range(7)
            ]
        elif slot.species == "oumuamua":
            slot.extra["tile"] = {"data": 0, "markers": [0, 1, 2]}
        elif slot.species == "centaurians":
            slot.extra["covered"] = [0, 1, 2, 1]
            for p in s.players:
                p.messages = [p.score + 15, p.score + 30]
        elif slot.species == "glyphids":
            kinds = sorted(set(glyphids.data()["glyphs"]))
            slot.extra["top"] = [kinds[0], kinds[1], kinds[2]]
            slot.extra["bottom"] = [kinds[3], kinds[4], kinds[5], kinds[6]]
        elif slot.species == "amoeba":
            ring = amoeba.data()["rings"]
            spaces = [sp for r in ("outer", "inner") for sp, _ in ring[r]]
            # the game has five organelles; for the review every one of the nine spaces holds one, to see each place
            slot.extra["organelles"] = {sp: rnd.randrange(len(amoeba.data()["organelles"])) for sp in spaces}
    return s


def view_json(s: GameState, legal: list[dict[str, Any]], notes: list[Any]) -> dict[str, Any]:
    v = project(s, 0, previews=False)
    out: dict[str, Any] = v.model_dump(mode="json")
    out["legal"], out["notes"], out["classes"] = legal, notes, ["answer"] * len(legal)
    out["reach"] = []
    return out


def main() -> None:
    out: list[dict[str, Any]] = []
    for n, (a, b) in enumerate(PAIRS):
        s, legal, notes = prompts(base_state(a, b, 100 + n))
        placed = markers(base_state(a, b, 100 + n), random.Random(n))
        out.append({"species": [a, b], "prompts": view_json(s, legal, notes), "markers": view_json(placed, [], [])})
        kinds: dict[str, int] = {}
        for m in legal:
            key = str(m["type"]) + (":" + str(m.get("space")) if m["type"] == "place_trace" else "")
            kinds[key] = kinds.get(key, 0) + 1
        print(f"{a} + {b}: {len(legal)} places offered {kinds}")
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"{OUT.name}: {OUT.stat().st_size // 1000} KB")


if __name__ == "__main__":
    main()
