"""Learning from the games of people with the bundle search (docs/AI-TURN-BUNDLES.md section 13): the human turn is offered to the search as a candidate.

A game of people teaches the model two things (owner, 2026-10-22), and neither is the exact move of a person:
1. that the bundles exist: the turn that a person played at a position is one more candidate for the search of the model at that position;
2. what they are worth: the model scores every candidate with its own value and the points it makes, and the policy learns from the one that scored best,
   whoever found it. The turn of the person is the target only when it is the best one.

`positions` replays a game and gives the start of each turn of a person with the turn that was played; `search_positions` runs the search from those starts
and makes the policy examples from the best bundle of each. The value of the positions of the same games (from the points that the seats really gained to the
end) comes from `dataset.py`, as before. Nothing here knows a rule: the engine says what a move is and when a turn ends (bundles.py).
"""

from __future__ import annotations

import copy
import json
import random
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from seti_engine import engine, orgs
from seti_engine.models import GameState, Options
from seti_engine.projection import actor_of, project, to_act
from seti_engine.replay import js_number

from . import dataset, features
from .bundle_data import Examples, PolicyExample, public_move
from .bundle_search import BundleSearch, History
from .bundles import TURN, bundles_of_game
from .knowledge import Knowledge


@dataclass
class Position:
    """The start of a turn of a person: the state as the game was at that moment (the search draws the hidden cards again), what the seat could have
    seen of the others, and the turn that was played."""

    game: str
    index: int  # the action number of the first move of the turn
    seat: int
    state: GameState
    history: History
    knowledge: Knowledge
    human: list[dict[str, Any]]
    options: Options


def bundle_examples(
    state: GameState, seat: int, history: History, knowledge: Knowledge | None, moves: list[dict[str, Any]], weight: float = 1.0, memory: bool = True
) -> list[PolicyExample]:
    """The policy examples of playing `moves` from `state`, one per move: the position before the move as `seat` sees it, and the move among the legal
    ones. It stops at a move that is not legal there (the bundle was found on another copy of the game)."""
    out: list[PolicyExample] = []
    hist = list(history)
    know = copy.deepcopy(knowledge) if knowledge is not None else Knowledge()
    for move in moves:
        if to_act(state) != seat or state.phase == "finished":
            break
        view = project(state, seat, previews=False)
        keep = [i for i, c in enumerate(view.classes) if c != "control"]
        if move not in view.legal or view.legal.index(move) not in keep:
            break
        toks, nums = features.encode_moves(view, keep)
        chosen = keep.index(view.legal.index(move))
        tokens = features.encode_view(view, hist if memory else None, know if memory else None)
        out.append(PolicyExample(tokens, toks, nums, chosen, weight))
        res = engine.apply(state, move)
        know.update(seat, move, res.events)
        hist.append((seat, public_move(move, res.events, seat)))
        state = res.state
    return out


def positions(
    options: Options,
    actions: list[dict[str, Any]],
    rng_encoding: str = "exact",
    game: str = "",
    skip_seats: frozenset[int] = frozenset(),
    limit: int | None = None,
    rng: random.Random | None = None,
) -> Iterator[Position]:
    """The start of every complete turn of the seats that are not in `skip_seats` (the seats of the model). With `limit` only that many turns, drawn at
    random with `rng`."""
    bundles, _ = bundles_of_game(options, actions, rng_encoding)
    turns = {
        b.steps[0].index: [m.move for m in b.steps]
        for b in bundles
        if b.kind == TURN and b.complete and b.seat not in skip_seats and all(m.move["type"] != "undo" for m in b.steps)
    }
    if limit is not None and len(turns) > limit:
        chosen = sorted((rng or random.Random(0)).sample(sorted(turns), limit))
        turns = {k: turns[k] for k in chosen}
    state = engine.start(options).state
    history: History = []
    know = Knowledge()
    for index, move in enumerate(actions):
        if rng_encoding == "double":
            state = state.model_copy()
            state.rng_state = js_number(state.rng_state)
        seat = actor_of(state, move)
        assert seat is not None
        if index in turns:
            yield Position(game, index, seat, state.model_copy(deep=True), list(history), copy.deepcopy(know), turns[index], options)
        if move["type"] == "undo":
            taken = state.undo_log[-1] if state.undo_log else None
            for k in range(len(history) - 1, -1, -1):
                h = {key: v for key, v in history[k][1].items() if key != "display_card"}
                if history[k][0] == seat and h == taken:
                    del history[k]
                    break
            state = engine.apply(state, move).state
            continue
        res = engine.apply(state, move)
        if move["type"] not in orgs.SETUP_TYPES:  # secret until all are locked in (EXP-ORG-14)
            know.update(seat, move, res.events)
            history.append((seat, public_move(move, res.events, seat)))
        state = res.state


def sample_positions(root: Path, count: int, seed: int, solo: bool = False) -> tuple[list[Position], dataset.Stats]:
    """About `count` turn starts from the usable games under `root` (the same games as `dataset.load_examples`), spread over the games, drawn by `seed`.
    A game that cannot be replayed any more is skipped and counted."""
    stats = dataset.Stats()
    games: list[dataset.ArchivedGame] = []
    for path in dataset.game_paths(root):
        stats.games += 1
        try:
            game = dataset.parse(dataset.load_file(path))
        except Exception:
            stats.skip("unreadable")
            continue
        why = dataset.skip_reason(game, solo)
        if why is not None:
            stats.skip(why)
            continue
        games.append(game)
    rng = random.Random(seed)
    out: list[Position] = []
    per_game = max(1, -(-count // max(len(games), 1)))
    rng.shuffle(games)
    for game in games:
        if len(out) >= count:
            break
        try:
            found = list(positions(game.options, game.actions, game.rng_encoding, game.id, frozenset(game.model_seats), min(per_game, count - len(out)), rng))
        except Exception:
            stats.skip("cannot be replayed")
            continue
        out += found
        stats.used += 1
    return out, stats


@dataclass
class ExpertStats:
    """What the search found at the positions: how often the turn of the person was the best one, and by how much a better one beat it."""

    positions: int = 0
    human_scored: int = 0  # the human turn could be played on the copy of the game and was scored
    human_best: int = 0  # ... and no candidate scored better
    margin: float = 0.0  # the points that the best candidate scored over the human one, summed over the positions where it was found
    best_longer: int = 0  # the best bundle had more moves than the human one
    best_shorter: int = 0
    origins: dict[str, int] = field(default_factory=dict)  # where the best bundles came from

    def __str__(self) -> str:
        n = max(self.human_scored, 1)
        return (
            f"{self.positions} positions, the turn of the person scored in {self.human_scored}; "
            f"it was the best in {self.human_best} ({self.human_best / n:.0%}), the best one beat it by {self.margin / n:.1f} points on average "
            f"({self.best_longer} longer, {self.best_shorter} shorter); the best came from {dict(sorted(self.origins.items()))}"
        )


def search_positions(
    found: list[Position], search: BundleSearch, rng: random.Random, weight: float = 1.0, memory: bool = True, offer: bool = True
) -> tuple[Examples, ExpertStats]:
    """Search from each position, with the turn of the person offered as a candidate (`offer`), and make the policy examples from the best bundle found.
    Without `offer` the search is the model's alone (to see what the offered bundles add)."""
    out, st = Examples(), ExpertStats()
    for pos in found:
        res = search.search(pos.state, pos.seat, pos.history, pos.knowledge, rng, offered=[pos.human] if offer else None)
        st.positions += 1
        best = res.best
        st.origins[best.origin] = st.origins.get(best.origin, 0) + 1
        human_key = json.dumps(pos.human, sort_keys=True)
        human = next((c for c in res.candidates if c.key == human_key), None)
        if human is not None:
            st.human_scored += 1
            st.human_best += human.key == best.key
            st.margin += best.score - human.score
            st.best_longer += len(best.moves) > len(pos.human)
            st.best_shorter += len(best.moves) < len(pos.human)
        assert res.start is not None
        out.policy += bundle_examples(res.start, pos.seat, pos.history, pos.knowledge, best.moves, weight, memory)  # on the copy it was found on
        out.bundles += 1
    return out, st
