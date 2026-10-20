"""The features: everything that a seat sees is in them, and nothing that it does not see."""

import random
import sys
from pathlib import Path

import numpy as np
from seti_engine import engine, species
from seti_engine.models import GameState, Options
from seti_engine.projection import project, to_act

from seti_ai import features

sys.path.insert(0, str(Path(__file__).parents[2] / "engine" / "tests"))


def tokens_equal(a: features.Tokens, b: features.Tokens) -> bool:
    return np.array_equal(a.kinds, b.kinds) and np.array_equal(a.offsets, b.offsets) and np.array_equal(a.idx, b.idx) and np.array_equal(a.val, b.val)


def play(seed: int, steps: int, **opts: object) -> GameState:
    rnd = random.Random(seed)
    r = engine.start(Options(players=2, seed=seed, **opts))  # type: ignore[arg-type]
    for _ in range(steps):
        if not r.legal:
            break
        r = engine.apply(r.state, rnd.choice(r.legal))
    return r.state


def test_the_tokens_are_the_same_for_the_same_view_and_cover_players_sectors_planets_and_species() -> None:
    s = play(3, 120)
    v = project(s, to_act(s), previews=False)
    a, b = features.encode_view(v), features.encode_view(v)
    assert tokens_equal(a, b) and np.isfinite(a.val).all() and a.offsets[-1] == len(a.idx) == len(a.val)
    kinds = {features._entity(p)[0] for p in ("state.players[0].score", "state.sectors[1].color", "state.planets.mars.orbiters", "state.species[0].species")}
    assert kinds == {"player", "sector", "planet", "species"}
    assert a.count > 30


def test_the_seats_are_made_relative() -> None:
    """Swapping the two players of a position gives the same features for the seat that is to act (both seats look alike to the network)."""
    s = play(5, 160)
    seat = to_act(s)
    assert seat is not None
    mine = features.relative_view(project(s, seat, previews=False))
    assert mine["state"]["players"][0]["score"] == s.players[seat].score
    assert mine["state"]["players"][1]["score"] == s.players[1 - seat].score
    for sec_new, sec_old in zip(mine["state"]["sectors"], s.sectors, strict=True):
        assert sec_new["markers"] == [(m - seat) % 2 if m in (0, 1) else m for m in sec_old.markers]


def test_nothing_hidden_gets_into_the_features() -> None:
    """The deck order, the other seat's hand, the face-down tiles and an undiscovered species are not seen: changing them changes nothing."""
    for seed in range(4):
        s = play(seed, 100 + 15 * seed)
        seat = to_act(s)
        if seat is None:
            continue
        base = features.encode_view(project(s, seat, previews=False))
        t = s.model_copy(deep=True)
        rnd = random.Random(seed)
        rnd.shuffle(t.deck)  # the deck order
        for stack in t.end_of_round_stacks:
            rnd.shuffle(stack)
        other = t.players[1 - seat]
        rnd.shuffle(other.hand)  # the other seat's hand (its identity, not its size)
        for st in t.tech_stacks:  # the tiles under the top one
            rest = st.tiles[1:]
            rnd.shuffle(rest)
            st.tiles = st.tiles[:1] + rest
        # the species that are not discovered: swap the two slots' identity and decks and boards
        if not t.species[0].discovered and not t.species[1].discovered:
            a, b = t.species
            a.species, b.species = b.species, a.species
            a.deck, b.deck = b.deck, a.deck
            a.board, b.board = b.board, a.board
            a.extra, b.extra = b.extra, a.extra
        again = features.encode_view(project(t, seat, previews=False))
        assert tokens_equal(base, again), seed


def test_an_undiscovered_species_is_the_same_whatever_it_is() -> None:
    names = ("anomalies", "centaurians", "exertians", "mascamites", "oumuamua")
    seen = []
    for first in names:
        s = engine.start(Options(players=2, seed=7)).state.model_copy(deep=True)
        s.species[0].species = first
        s.species[0].board = species.new_board(first)
        seat = to_act(s)
        assert seat is not None
        seen.append(features.encode_view(project(s, seat, previews=False)))
    assert all(tokens_equal(seen[0], x) for x in seen[1:])


def test_a_discovered_species_and_its_own_state_are_seen() -> None:
    """The species, its discovery spaces, its board and its per-species state (anomaly tokens, milestones, the tile of 'Oumuamua) are features."""
    s = play(2, 40)
    seat = to_act(s)
    assert seat is not None
    s.species[0].species = "anomalies"
    s.species[0].discovered = True
    s.species[0].board = species.new_board("anomalies")
    s.species[0].extra = {"tokens": [{"sector": 7, "color": "pink", "side": 0, "reward": [{"n": 1, "t": "credit"}]}]}
    plain = play(2, 40)
    a = features.encode_view(project(s, seat, previews=False))
    b = features.encode_view(project(plain, seat, previews=False))
    assert not np.array_equal(a.idx, b.idx)
    assert any(features._entity(p)[0] == "species.extra" for p in ("state.species[0].extra.tokens",))


def test_the_memory_gives_a_token_for_each_of_the_last_actions_and_hides_a_card_that_went_unseen() -> None:
    s = play(4, 60)
    seat = to_act(s)
    assert seat is not None
    view = project(s, seat, previews=False)
    history = [(0, {"type": "play_card", "card": "27"}), (1, {"type": "tuck", "card": "76"}), (0, {"type": "launch"})]
    plain = features.encode_view(view)
    with_memory = features.encode_view(view, history)
    assert with_memory.count == plain.count + 3
    other = [(0, {"type": "play_card", "card": "27"}), (1, {"type": "tuck", "card": "99"}), (0, {"type": "launch"})]
    assert tokens_equal(with_memory, features.encode_view(view, other))  # which card was tucked is not seen
    changed = [(0, {"type": "play_card", "card": "28"}), (1, {"type": "tuck", "card": "76"}), (0, {"type": "launch"})]
    assert not tokens_equal(with_memory, features.encode_view(view, changed))  # a card that was played is seen
    long = [(i % 2, {"type": "launch"}) for i in range(200)]
    assert features.encode_view(view, long).count == plain.count + features.HISTORY_LEN


def test_the_arena_keeps_the_history_of_both_seats() -> None:
    from seti_ai import arena, bots

    class Spy(bots.RandomBot):
        seen = 0

        def act(self, state, view, rng):  # type: ignore[no-untyped-def]
            Spy.seen = max(Spy.seen, len(self.history))
            return super().act(state, view, rng)

    res = arena.play_game([Spy(), bots.RandomBot()], 3)
    assert Spy.seen > 20 and res.finished
