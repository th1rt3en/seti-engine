"""Bundle search (stage B of docs/AI-TURN-BUNDLES.md): at the start of a turn, build several whole turns, score each, play the best one.

A candidate bundle is a list of moves that takes the seat from the start of its turn to the end of it (free actions, the main action with its answers,
free actions). Candidates come from three places:
- **offered**: bundles that the caller brings (the turn that a person played at this position, docs/AI-TURN-BUNDLES.md section 13); they are scored like
  any other, and get neighbours like any other, so the model finds out what they are worth with its own value;
- **samples**: the policy plays the turn on a copy of the game, one micro move after another (one greedy rollout, the others sampled);
- **neighbours** of the best samples: the same bundle with one free action added (at any place where the engine offers one), one taken away, or one
  moved to the other side of the main action. A longer or shorter bundle that is better is found even when the policy would hardly ever have played
  it.

A candidate is scored by `points gained in the bundle + the value of the position after it` (the value is the expected number of points the seat still
gains, from `Brain.value`), on a few copies of the game in which the hidden cards of the opponent (and the order of the deck) are drawn again: the bot
never reads the real hand of the opponent. The best candidate is played; its moves are given out one by one as the game asks for the next move.

The module knows no rule: moves, their classes and the end of a turn come from the engine (`legal_classified`, `bundles.bundle_key`). Not drawn again
(a limit, written down in docs/AI-TURN-BUNDLES.md): the face-down end-of-round cards, the alien species decks, the Exertian hands.
"""

from __future__ import annotations

import copy
import json
import random
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np
from seti_engine import engine
from seti_engine.models import GameState
from seti_engine.projection import View, to_act

from .bundles import bundle_key
from .knowledge import Knowledge
from .views import project

History = list[tuple[int, dict[str, Any]]]

# A search can ask a brain for many things at once: a process (a generator) yields a list of requests, `("logits", view, history, knowledge)` or
# `("value", state, seat, history, knowledge)`, and is sent the list of answers. `drive` runs several processes in lockstep and answers all their
# requests together, so that a network is called once for a whole batch (docs/AI-MCTS.md, Step 0); with one process it is the plain sequential search.
Request = tuple[Any, ...]
Process = Generator[list[Request], list[Any], Any]


def answer(brain: Brain, requests: list[Request]) -> list[Any]:
    """The answers to the requests, in order: all at once if the brain can (`answer_many`), else one by one."""
    many = getattr(brain, "answer_many", None)
    if many is not None:
        return list(many(requests))
    out: list[Any] = []
    for r in requests:
        out.append(brain.logits(r[1], r[2], r[3]) if r[0] == "logits" else brain.value(r[1], r[2], r[3], r[4]))
    return out


def drive(processes: list[Process], brain: Brain) -> list[Any]:
    """Run the processes together until all are done; their results, in order."""
    results: list[Any] = [None] * len(processes)
    waiting: dict[int, list[Request]] = {}

    def step(i: int, reply: list[Any] | None) -> None:
        try:
            waiting[i] = processes[i].send(reply)  # type: ignore[arg-type]
        except StopIteration as stop:
            results[i] = stop.value
            waiting.pop(i, None)

    for i in range(len(processes)):
        step(i, None)
    while waiting:
        who = list(waiting)
        flat = [r for i in who for r in waiting[i]]
        replies = answer(brain, flat)
        at = 0
        for i in who:
            n = len(waiting[i])
            step(i, replies[at : at + n])
            at += n
    return results


def parallel(processes: list[Process]) -> Process:
    """A process that runs the others side by side, joining their requests into one list at each step; its result is the list of their results."""
    results: list[Any] = [None] * len(processes)
    waiting: dict[int, list[Request]] = {}

    def step(i: int, reply: list[Any] | None) -> None:
        try:
            waiting[i] = processes[i].send(reply)  # type: ignore[arg-type]
        except StopIteration as stop:
            results[i] = stop.value
            waiting.pop(i, None)

    for i in range(len(processes)):
        step(i, None)
    while waiting:
        who = list(waiting)
        replies = yield [r for i in who for r in waiting[i]]
        at = 0
        for i in who:
            n = len(waiting[i])
            step(i, replies[at : at + n])
            at += n
    return results


class Brain(Protocol):
    """What the search needs to know from a network (or from anything else that can score moves and positions)."""

    def logits(self, view: View, history: History, knowledge: Knowledge | None) -> np.ndarray:
        """One score for each legal move of the view (`len(view.legal)`), the higher the better; `undo` is never chosen by the search."""

    def value(self, state: GameState, seat: int, history: History, knowledge: Knowledge | None) -> float:
        """The points that the seat is expected to gain from this position (the one after its bundle) to the end of the game."""


@dataclass
class SearchConfig:
    samples: int = 6  # bundles played by sampling the policy (one more is played greedily)
    temperature: float = 1.0
    keep: int = 2  # the best bundles that get neighbours
    neighbours: int = 12  # at most this many neighbours of each kept bundle
    finalists: int = 4  # the best candidates are scored again on the other copies of the game
    copies: int = 3  # copies of the game with the hidden cards drawn again
    max_micro: int = 80  # a bundle is cut off after this many moves (a safeguard)
    # Self-play explores: with a temperature above 0 the bundle that is played is drawn among the finalists, a candidate that is `t` points worse than
    # the best being `exp(-t / pick_temperature)` as likely. 0 plays the best one (as the bot in the lobby does).
    pick_temperature: float = 0.0


@dataclass
class Candidate:
    moves: list[dict[str, Any]]
    points: float  # the points gained in the bundle (the mean over the copies where it could be played)
    value: float  # the value of the position after it (the same mean)
    origin: str  # "greedy", "sample", "offered", "add", "remove", "move"
    plays: int = 1  # on how many copies it could be played from the first move to the last as it is

    @property
    def score(self) -> float:
        return self.points + self.value

    @property
    def key(self) -> str:
        return json.dumps(self.moves, sort_keys=True)


@dataclass
class SearchResult:
    best: Candidate
    candidates: list[Candidate] = field(default_factory=list)
    # the copy of the game that the candidates were made on (the hidden cards drawn again): they are exactly legal there. On the real game a move that
    # depends on
    # a chance event (the card that is drawn, for example) may not be what was planned: the bot then searches again from where the game is.
    start: GameState | None = None
    # the bundle that is played: the best one, or (self-play, `pick_temperature` above 0) one drawn among the finalists
    played: Candidate | None = None
    # for the tree search: how many times each bundle (by its key) was visited, added over the worlds
    visits: dict[str, int] = field(default_factory=dict)


def determinize(state: GameState, seat: int, knowledge: Knowledge | None, rng: random.Random) -> GameState:
    """A copy of the game as `seat` can imagine it: the deck in another order and the cards of the opponents that the seat has not seen drawn again from
    what it has not seen (the deck and those cards together); the cards that it knows are in a hand (taken from the display, shown) stay there. The
    result does not depend on the order of the unseen cards in the real state: only on which cards they are."""
    s = state.model_copy(deep=True)
    pool = list(s.deck)
    holders: list[tuple[Any, list[str], int]] = []
    for p in s.players:
        if p.index == seat or (s.rival is not None and p.index == s.rival.index):
            continue
        known = list(knowledge.of(p.index)) if knowledge is not None else []
        unseen = list(p.hand)
        kept: list[str] = []
        for c in known:
            if c in unseen:
                unseen.remove(c)
                kept.append(c)
        holders.append((p, kept, len(unseen)))
        pool += unseen
    pool.sort()
    rng.shuffle(pool)
    for p, kept, n in holders:
        p.hand = kept + pool[:n]
        pool = pool[n:]
    s.deck = pool
    s.rng_state = rng.getrandbits(62)
    return s


@dataclass
class _Rollout:
    moves: list[dict[str, Any]]
    end: GameState
    history: History
    knowledge: Knowledge
    followed: bool  # the plan was followed to its last move, and each of its moves was legal when its turn came
    logp: float = 0.0  # the log probability that the policy gave to the moves it chose itself (not to those of the plan)


def _final_total(state: GameState, seat: int) -> float:
    for row in state.final_scores:
        if row.get("player") == seat:
            return float(row.get("total", state.players[seat].score))
    return float(state.players[seat].score)


def play_bundle_g(
    state0: GameState,
    seat: int,
    history: History,
    knowledge: Knowledge | None,
    rng: random.Random,
    *,
    plan: list[dict[str, Any]] | None = None,
    greedy: bool = False,
    temperature: float = 1.0,
    max_micro: int = 80,
    irreversible: bool | None = None,
) -> Process:
    """Play the rest of the bundle on a copy: the moves of `plan` while they are legal, then the policy (the best move if `greedy`, else sampled), until
    the turn passes to someone else. A process (see `drive`)."""
    state = state0
    start = bundle_key(state, seat)
    hist = list(history)
    know = copy.deepcopy(knowledge) if knowledge is not None else Knowledge()
    moves: list[dict[str, Any]] = []
    pos = 0
    followed = plan is not None
    logp = 0.0
    for _ in range(max_micro):
        classified = [(m, c) for m, c in engine.legal_classified(state) if c != "control"]
        if not classified:
            break
        move: dict[str, Any] | None = None
        if plan is not None and pos < len(plan):
            if any(m == plan[pos] for m, _ in classified):
                move = plan[pos]
                pos += 1
            else:
                followed = False  # the plan does not fit this copy of the game any more: go on with the policy
                plan = None
        if move is None:
            view = project(state, seat, previews=False, irreversible=irreversible)
            scores = np.asarray((yield [("logits", view, hist, know)])[0], dtype=np.float64)
            ok = [i for i, m in enumerate(view.legal) if view.classes[i] != "control"]
            if not ok:
                break
            sub = scores[ok]
            if greedy or len(ok) == 1:
                at = int(np.argmax(sub))
            else:
                z = (sub - sub.max()) / max(temperature, 1e-6)
                p = np.exp(z)
                p /= p.sum()
                at = int(rng.choices(range(len(ok)), weights=p.tolist())[0])
            pick = ok[at]
            logp += float(sub[at] - sub.max() - np.log(np.exp(sub - sub.max()).sum()))
            move = view.legal[pick]
        res = engine.apply(state, move)
        know.update(seat, move, res.events)
        hist.append((seat, move))
        moves.append(move)
        state = res.state
        if state.phase == "finished" or to_act(state) != seat or bundle_key(state, seat) != start:
            break
    if plan is not None and pos < len(plan):
        followed = False  # the bundle ended before the plan did
    return _Rollout(moves, state, hist, know, followed, logp)


def play_bundle(state0: GameState, seat: int, brain: Brain, history: History, knowledge: Knowledge | None, rng: random.Random, **kw: Any) -> _Rollout:
    """`play_bundle_g` run alone (sequentially)."""
    kw.setdefault("irreversible", getattr(brain, "irreversible", None))
    rollout: _Rollout = drive([play_bundle_g(state0, seat, history, knowledge, rng, **kw)], brain)[0]
    return rollout


def _points(end: GameState, start: GameState, seat: int) -> float:
    before = start.players[seat].score
    if end.phase == "finished":
        return float(_final_total(end, seat) - before)
    return float(end.players[seat].score - before)


class BundleSearch:
    def __init__(self, brain: Brain, config: SearchConfig | None = None) -> None:
        self.brain = brain
        self.cfg = config or SearchConfig()

    def _score(
        self, state0: GameState, seat: int, moves: list[dict[str, Any]], history: History, knowledge: Knowledge | None, rng: random.Random
    ) -> Candidate | None:
        """Play exactly these moves on a copy of the game; give the candidate with its points and the value after it (None if it cannot be played as it
        is)."""
        r = play_bundle(state0, seat, self.brain, history, knowledge, rng, plan=moves, greedy=True, max_micro=self.cfg.max_micro)
        if not r.followed:
            return None
        v = 0.0 if r.end.phase == "finished" else self.brain.value(r.end, seat, r.history, r.knowledge)
        return Candidate(r.moves, _points(r.end, state0, seat), v, "")

    def _edits(self, state0: GameState, seat: int, moves: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
        """The neighbours of a bundle: one free action added where the engine offers one, one taken out, or one moved to the other side of the main
        action."""
        out: list[tuple[str, list[dict[str, Any]]]] = []
        state = state0
        classes: list[str] = []
        free_at: list[list[dict[str, Any]]] = []
        for m in moves:
            classified = engine.legal_classified(state)
            classes.append(next((c for mm, c in classified if mm == m), ""))
            free_at.append([mm for mm, c in classified if c == "free" and mm != m])
            state = engine.apply(state, m).state
        free_at.append([mm for mm, c in engine.legal_classified(state) if c == "free"])  # after the last move
        for i, options in enumerate(free_at):
            for f in options:
                out.append(("add", moves[:i] + [f] + moves[i:]))
        main_at = next((i for i, c in enumerate(classes) if c == "main"), None)
        for i, c in enumerate(classes):
            if c == "free":
                out.append(("remove", moves[:i] + moves[i + 1 :]))
                if main_at is not None:
                    # to the other side of the main action: a free action before it goes right after it, one after it goes right before it (in both cases the
                    # same place in the list without the moved move)
                    rest = moves[:i] + moves[i + 1 :]
                    out.append(("move", rest[:main_at] + [moves[i]] + rest[main_at:]))
        return out

    def search(
        self,
        state: GameState,
        seat: int,
        history: History,
        knowledge: Knowledge | None,
        rng: random.Random,
        offered: list[list[dict[str, Any]]] | None = None,
    ) -> SearchResult:
        """`offered` are bundles (lists of moves) that are scored as candidates besides the sampled ones; one that cannot be played as it is on the copy of
        the game (a move that is not legal there) is dropped."""
        cfg = self.cfg
        copies = [determinize(state, seat, knowledge, rng) for _ in range(cfg.copies)]
        d0 = copies[0]
        found: dict[str, Candidate] = {}

        def add(c: Candidate | None, origin: str) -> None:
            if c is None or not c.moves:
                return
            c.origin = origin
            if c.key not in found or found[c.key].score < c.score:
                found[c.key] = c

        def play_and_score(greedy: bool, origin: str) -> None:
            r = play_bundle(d0, seat, self.brain, history, knowledge, rng, greedy=greedy, temperature=cfg.temperature, max_micro=cfg.max_micro)
            v = 0.0 if r.end.phase == "finished" else self.brain.value(r.end, seat, r.history, r.knowledge)
            add(Candidate(r.moves, _points(r.end, d0, seat), v, origin), origin)

        play_and_score(True, "greedy")
        for _ in range(cfg.samples):
            play_and_score(False, "sample")
        for moves in offered or []:
            add(self._score(d0, seat, [dict(m) for m in moves], history, knowledge, rng), "offered")

        best_first = sorted(found.values(), key=lambda c: -c.score)
        for base in best_first[: cfg.keep]:
            edits = self._edits(d0, seat, base.moves)
            rng.shuffle(edits)
            for origin, moves in edits[: cfg.neighbours]:
                add(self._score(d0, seat, moves, history, knowledge, rng), origin)

        finalists = sorted(found.values(), key=lambda c: -c.score)[: cfg.finalists]
        for c in finalists:  # the same bundle on the other copies of the game: the mean of those where it can be played as it is
            pts, vals, n = [c.points], [c.value], 1
            for other in copies[1:]:
                r = self._score(other, seat, c.moves, history, knowledge, rng)
                if r is not None:
                    pts.append(r.points)
                    vals.append(r.value)
                    n += 1
            c.points, c.value, c.plays = float(np.mean(pts)), float(np.mean(vals)), n
        best = max(finalists, key=lambda c: (c.score, c.plays))
        played = best
        if cfg.pick_temperature > 0 and len(finalists) > 1:
            weights = [float(np.exp((c.score - best.score) / cfg.pick_temperature)) for c in finalists]
            played = rng.choices(finalists, weights=weights)[0]
        return SearchResult(best, sorted(found.values(), key=lambda c: -c.score), d0, played)


class BundleBot:
    """Plays with the bundle search: at the start of a turn it searches, then gives out the moves of the best bundle one by one (a search again if the
    game does not ask for the move that was planned). Like the other bots it has `act(state, view, rng)`, and `history` and `knowledge` that the arena
    sets."""

    name = "bundle-search"

    def __init__(self, brain: Brain, config: SearchConfig | None = None, search: Any = None) -> None:
        self.search = search if search is not None else BundleSearch(brain, config)  # or the tree search (`mcts.make_search`)
        self.history: History | None = None
        self.knowledge: Knowledge | None = None
        self.plan: list[dict[str, Any]] = []
        self.pos = 0
        self.key: tuple[str, tuple[int, int, int]] | None = None
        self.last: SearchResult | None = None  # what the last search found, for the log of the training and of the games
        self.searches = 0

    def act(self, state: GameState, view: View, rng: random.Random) -> int:
        seat = view.viewer
        assert seat is not None
        key = bundle_key(state, seat)
        planned = self.plan[self.pos] if self.key == key and self.pos < len(self.plan) else None
        if planned is None or planned not in view.legal:
            self.last = self.search.search(state, seat, self.history if self.history is not None else [], self.knowledge, rng)
            self.searches += 1
            self.plan, self.pos, self.key = list((self.last.played or self.last.best).moves), 0, key
            planned = self.plan[0] if self.plan else None
        if planned is None or planned not in view.legal:  # nothing found (should not happen): any move that is not an undo
            usable = [i for i, m in enumerate(view.legal) if m["type"] != "undo"] or list(range(len(view.legal)))
            return usable[0]
        self.pos += 1
        return int(view.legal.index(planned))
