"""Tree search over turns (docs/AI-MCTS.md, Steps 0 to 2): PUCT over whole bundles, in several determinized worlds, with the network called for batches.

What a node is: the game at the start of a seat's turn, in one world (the hidden cards of the opponent and the order of the deck drawn again, as
`bundle_search.determinize` does). What an edge is: a bundle, a whole turn, that the policy made there (one greedy and a few sampled; at the root also the
neighbours of the best ones and the turn that a person played). A bundle is valued by the points of both seats after it:

    D(position) = (own score + the value of the own seat) - (the opponent's score + the value of the opponent's seat)

so the tree plays for a win and denies the opponent, and a position where the opponent is to move is searched with the opponent's own policy (the reply of
the opponent is in the tree, which the search of `bundle_search` does not have). The values come from the network's value head, which is trained on the
points that a seat still gains, called once for each seat.

How a search goes:
1. the root bundles are made in the first world (as the old search does) and played again in the other worlds, where each becomes an edge of that world's tree;
2. each world runs its simulations: a path of edges is chosen by PUCT (`Q + c * P * sqrt(N) / (1 + n)`, the value taken from the point of view of the seat that
   moves), the node at its end is expanded (its bundles are made and valued), the value of the edge is backed up. Several simulations of a world are
   made together with a virtual loss, and all the worlds advance in lockstep, so a network call answers many requests at once (`bundle_search.drive`);
3. the visits of each root bundle are added over the worlds; the most visited bundle is played (self-play with a temperature draws among the best).

Known limits (written in the design): each world acts as if it knew its cards (strategy fusion); the chance of the engine is drawn once for each edge, not
for each visit; the neighbours and the offered bundles have no prior of their own (the mean of the sampled ones is used).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

import numpy as np
from seti_engine.models import GameState
from seti_engine.projection import to_act

from .bundle_search import (
    BundleSearch,
    Candidate,
    History,
    Process,
    SearchConfig,
    SearchResult,
    _final_total,
    determinize,
    drive,
    parallel,
    play_bundle_g,
)
from .knowledge import Knowledge


@dataclass
class MCTSConfig(SearchConfig):
    simulations: int = 48  # node expansions in all, shared by the worlds
    worlds: int = 4  # determinized worlds, each with its own tree
    leaves: int = 4  # simulations of a world that are made together (virtual loss)
    branch: int = 6  # bundles made at a node: one greedy and the others sampled
    c_puct: float = 1.5
    q_scale: float = 10.0  # points that count as 1 in the selection


def make_search(brain: Any, config: SearchConfig | None = None) -> Any:
    """The search that the configuration asks for: the tree search for an `MCTSConfig`, else the search of one turn."""
    if isinstance(config, MCTSConfig):
        return MCTS(brain, config)
    return BundleSearch(brain, config)


@dataclass
class _Edge:
    moves: list[dict[str, Any]]
    key: str
    prior: float
    est: float  # D after the bundle, from the root seat's side
    end: GameState
    hist: History
    know: Knowledge
    origin: str = "sample"
    n: int = 0
    w: float = 0.0
    vl: int = 0
    child: _Node | None = None

    @property
    def terminal(self) -> bool:
        return bool(self.end.phase == "finished")


@dataclass
class _Node:
    state: GameState
    hist: History
    know: Knowledge
    edges: list[_Edge] | None = None
    n: int = 0
    pending: bool = False


def _opponents(state: GameState, seat: int) -> list[int]:
    return [p.index for p in state.players if p.index != seat and not (state.rival is not None and p.index == state.rival.index)]


def _value_requests(state: GameState, seat: int, hist: History, know: Knowledge) -> list[tuple[Any, ...]]:
    if state.phase == "finished":
        return []
    return [("value", state, s, hist, know if s == seat else Knowledge()) for s in [seat, *_opponents(state, seat)]]


def _difference(state: GameState, seat: int, values: list[float]) -> float:
    """D of a position from the answers to its value requests (in the order made by `_value_requests`; none when the game is over)."""
    others = _opponents(state, seat)
    if state.phase == "finished":
        own = _final_total(state, seat)
        theirs = [_final_total(state, o) for o in others]
    else:
        own = state.players[seat].score + values[0]
        theirs = [state.players[o].score + v for o, v in zip(others, values[1:], strict=True)]
    return float(own - (sum(theirs) / len(theirs) if theirs else 0.0))


def _key(moves: list[dict[str, Any]]) -> str:
    import json

    return json.dumps(moves, sort_keys=True)


class MCTS:
    def __init__(self, brain: Any, config: MCTSConfig | None = None) -> None:
        self.brain = brain
        self.cfg = config or MCTSConfig()
        self.irreversible = getattr(brain, "irreversible", None)  # the views of this brain (views.py)
        self._edits = BundleSearch(brain, self.cfg)._edits  # the neighbours of a bundle (no rule of its own: the engine says what is legal)

    # ---------------------------------------------------------------------------------------------------------------- edges

    def _make_edges(self, node: _Node, root_seat: int, rng: random.Random, plans: list[tuple[list[dict[str, Any]], str]] | None = None) -> Process:
        """The edges of a node: with `plans` the given bundles replayed here (those that cannot be played as they are, are dropped), else a greedy bundle
        and `branch - 1` sampled ones made by the policy of the seat that moves."""
        cfg = self.cfg
        mover = to_act(node.state)
        if mover is None:
            return []
        know = node.know if mover == root_seat else Knowledge()
        if plans is None:
            jobs = [
                play_bundle_g(
                    node.state,
                    mover,
                    node.hist,
                    know,
                    random.Random(rng.getrandbits(62)),
                    greedy=k == 0,
                    temperature=cfg.temperature,
                    max_micro=cfg.max_micro,
                    irreversible=self.irreversible,
                )
                for k in range(cfg.branch)
            ]
            origins = ["greedy"] + ["sample"] * (cfg.branch - 1)
        else:
            jobs = [
                play_bundle_g(
                    node.state,
                    mover,
                    node.hist,
                    know,
                    random.Random(rng.getrandbits(62)),
                    plan=moves,
                    greedy=True,
                    max_micro=cfg.max_micro,
                    irreversible=self.irreversible,
                )
                for moves, _ in plans
            ]
            origins = [o for _, o in plans]
        rolls = yield from parallel(jobs)
        kept: list[tuple[Any, str]] = []
        seen: set[str] = set()
        for r, o in zip(rolls, origins, strict=True):
            if not r.moves or (plans is not None and not r.followed) or _key(r.moves) in seen:
                continue
            seen.add(_key(r.moves))
            kept.append((r, o))
        asks = [_value_requests(r.end, root_seat, r.history, r.knowledge) for r, _ in kept]
        flat = [q for a in asks for q in a]
        answers = (yield flat) if flat else []
        edges: list[_Edge] = []
        at = 0
        for (r, o), a in zip(kept, asks, strict=True):
            vals = [float(x) for x in answers[at : at + len(a)]]
            at += len(a)
            edges.append(_Edge(r.moves, _key(r.moves), r.logp, _difference(r.end, root_seat, vals), r.end, r.history, r.knowledge, o))
        # the prior of a bundle: the softmax of its log probability among the bundles of the node (the root is set again in `search`)
        if edges:
            top = max(e.prior for e in edges)
            z = [math.exp(e.prior - top) for e in edges]
            total = sum(z)
            for e, x in zip(edges, z, strict=True):
                e.prior = x / total
        return edges

    # ---------------------------------------------------------------------------------------------------------------- selection

    def _pick(self, node: _Node, root_seat: int) -> _Edge:
        cfg = self.cfg
        assert node.edges
        mover = to_act(node.state)
        sign = 1.0 if mover == root_seat else -1.0
        best, best_score = node.edges[0], -1e18
        for e in node.edges:
            n1 = e.n + 1  # the value of the bundle itself counts as one visit
            q = (sign * (e.w + e.est) / cfg.q_scale - e.vl) / (n1 + e.vl)
            u = cfg.c_puct * e.prior * math.sqrt(node.n + 1) / (1 + e.n + e.vl)
            if q + u > best_score:
                best, best_score = e, q + u
        return best

    def _select(self, root: _Node, root_seat: int) -> tuple[list[tuple[_Node, _Edge]], _Node | None]:
        """A path of edges from the root, and the node at its end that has to be expanded (None: the end is a leaf whose value is already known)."""
        path: list[tuple[_Node, _Edge]] = []
        node = root
        while True:
            if not node.edges:
                return path, None
            e = self._pick(node, root_seat)
            e.vl += 1
            path.append((node, e))
            if e.terminal:
                return path, None
            if e.child is None:
                e.child = _Node(e.end, e.hist, e.know)
            node = e.child
            if node.edges is None:
                if node.pending:
                    return path, None
                node.pending = True
                return path, node

    @staticmethod
    def _back(path: list[tuple[_Node, _Edge]], value: float) -> None:
        for node, e in path:
            e.vl -= 1
            e.n += 1
            e.w += value
            node.n += 1

    # ---------------------------------------------------------------------------------------------------------------- one world

    def _world(self, root: _Node, root_seat: int, sims: int, rng: random.Random) -> Process:
        done = 0
        while done < sims:
            k = min(self.cfg.leaves, sims - done)
            picks = [self._select(root, root_seat) for _ in range(k)]
            fresh = [n for _, n in picks if n is not None]
            if fresh:
                made = yield from parallel([self._make_edges(n, root_seat, rng) for n in fresh])
                for n, edges in zip(fresh, made, strict=True):
                    n.edges, n.pending = edges, False
            for path, _ in picks:
                self._back(path, path[-1][1].est if path else 0.0)
            done += k

    # ---------------------------------------------------------------------------------------------------------------- search

    def search(
        self,
        state: GameState,
        seat: int,
        history: History,
        knowledge: Knowledge | None,
        rng: random.Random,
        offered: list[list[dict[str, Any]]] | None = None,
    ) -> SearchResult:
        cfg = self.cfg
        worlds = [determinize(state, seat, knowledge, rng) for _ in range(cfg.worlds)]
        know = knowledge if knowledge is not None else Knowledge()
        roots = [_Node(w, list(history), know) for w in worlds]
        wrngs = [random.Random(rng.getrandbits(62)) for _ in worlds]

        # the root bundles, made in the first world: the policy's own, the turns offered, and the neighbours of the best ones
        first = drive([self._make_edges(roots[0], seat, wrngs[0], None)], self.brain)[0]
        asked: list[tuple[list[dict[str, Any]], str]] = [([dict(m) for m in moves], "offered") for moves in offered or []]
        extra = drive([self._make_edges(roots[0], seat, wrngs[0], asked)], self.brain)[0] if asked else []
        base = sorted([*first, *extra], key=lambda e: -e.est)
        neighbours: list[tuple[list[dict[str, Any]], str]] = []
        for e in base[: cfg.keep]:
            edits = self._edits(worlds[0], seat, e.moves)
            wrngs[0].shuffle(edits)
            neighbours += [(m, o) for o, m in edits[: cfg.neighbours]]
        more = drive([self._make_edges(roots[0], seat, wrngs[0], neighbours)], self.brain)[0] if neighbours else []
        found: dict[str, _Edge] = {}
        for e in [*first, *extra, *more]:
            if e.key not in found or found[e.key].est < e.est:
                found[e.key] = e
        if not found:
            raise RuntimeError("the search found no bundle")
        if len(found) == 1:  # one bundle only (a turn with no choice): nothing to search
            only = next(iter(found.values()))
            c = Candidate(only.moves, 0.0, only.est, only.origin, 1)
            return SearchResult(c, [c], worlds[0], c, {c.key: 1})
        # the priors of the root, shared by all worlds: the policy's own bundles by their probability, the others (neighbours, offered) by the mean of those
        own = [e.prior for e in found.values() if e.origin in ("greedy", "sample")]
        mean_own = float(np.mean(own)) if own else 1.0
        raw = {k: (e.prior if e.origin in ("greedy", "sample") else mean_own) for k, e in found.items()}
        plan_all = [(e.moves, e.origin) for e in found.values()]

        def set_priors(edges: list[_Edge]) -> None:
            total = sum(raw[e.key] for e in edges) or 1.0
            for e in edges:
                e.prior = raw[e.key] / total

        # the same bundles in every world (the first one has them already), then the simulations of each world
        def build(i: int) -> Process:
            if i == 0:
                roots[0].edges = list(found.values())
            else:
                roots[i].edges = yield from self._make_edges(roots[i], seat, wrngs[i], plan_all)
            set_priors(roots[i].edges or [])
            yield from self._world(roots[i], seat, max(1, cfg.simulations // cfg.worlds), wrngs[i])

        drive([build(i) for i in range(cfg.worlds)], self.brain)

        # the visits of each root bundle, added over the worlds
        total: dict[str, dict[str, Any]] = {}
        for root in roots:
            for e in root.edges or []:
                t = total.setdefault(e.key, {"moves": e.moves, "origin": e.origin, "n": 0, "w": 0.0, "plays": 0})
                t["n"] += e.n
                t["w"] += e.w + e.est  # the value of the bundle itself counts as one visit
                t["plays"] += 1
        cands = [Candidate(t["moves"], 0.0, t["w"] / (t["n"] + t["plays"]), t["origin"], t["plays"]) for t in total.values()]
        visits = {c.key: total[c.key]["n"] for c in cands}
        ranked = sorted(cands, key=lambda c: (-visits[c.key], -c.score))
        best = ranked[0]
        played = best
        finalists = ranked[: cfg.finalists]
        if cfg.pick_temperature > 0 and len(finalists) > 1:
            top_q = max(c.score for c in finalists)
            weights = [float(np.exp((c.score - top_q) / cfg.pick_temperature)) for c in finalists]
            played = rng.choices(finalists, weights=weights)[0]
        return SearchResult(best, ranked, worlds[0], played, visits)
