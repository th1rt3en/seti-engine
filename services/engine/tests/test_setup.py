"""Setup rules: SETUP-10 to SETUP-38, A-003, A-004 (docs/spec/setup.md)."""

import pytest

from seti_engine import tables
from seti_engine.models import Options
from seti_engine.setup import new_game


def game(players: int = 3, seed: int = 11, promo: bool = False):
    return new_game(Options(players=players, seed=seed, promo_cards=promo))


@pytest.mark.parametrize("n", [2, 3, 4])
def test_card_counts(n: int) -> None:
    """SETUP-13, SETUP-17, SETUP-36: card row 3, 4 stacks of n+1, 5 cards each; 138 cards in all."""
    s = game(n)
    assert len(s.card_row) == 3
    assert [len(x) for x in s.end_of_round_stacks] == [n + 1] * 4
    assert all(len(p.hand) == 5 for p in s.players)
    dealt = 3 + 4 * (n + 1) + 5 * n
    assert len(s.deck) == 138 - dealt
    everything = s.deck + s.card_row + [c for st in s.end_of_round_stacks for c in st] + [c for p in s.players for c in p.hand]
    assert len(everything) == len(set(everything)) == 138


def test_promo_cards_are_an_option() -> None:
    """D23: SE EN 01 and 02 join the deck only when the option is on."""
    off, on = game(promo=False), game(promo=True)
    ids_off = set(off.deck + off.card_row + [c for st in off.end_of_round_stacks for c in st] + [c for p in off.players for c in p.hand])
    ids_on = set(on.deck + on.card_row + [c for st in on.end_of_round_stacks for c in st] + [c for p in on.players for c in p.hand])
    assert len(ids_off) == 138 and len(ids_on) == 140
    assert ids_on - ids_off == {"SE_EN_01", "SE_EN_02"}


@pytest.mark.parametrize("n", [2, 3, 4])
def test_starting_resources_and_scores(n: int) -> None:
    """SETUP-32 to SETUP-35: 4 publicity, 4 credits, 3 energy; scores 1, 2, 3, 4 in turn order from the starting player."""
    s = game(n)
    for rank in range(n):
        p = s.players[(s.start_player + rank) % n]
        assert (p.publicity, p.credits, p.energy, p.score) == (4, 4, 3, rank + 1)
    assert s.current_player == s.start_player


@pytest.mark.parametrize("n,per", [(2, 2), (3, 1), (4, 0)])
def test_neutral_milestones(n: int, per: int) -> None:
    """SETUP-20."""
    assert game(n).neutral_markers == {"20": per, "30": per}


def test_sectors_come_in_pairs() -> None:
    """BOARD-20: four boards, each keeps its two stars together; capacities 4 to 6; 8 sectors; every color twice."""
    s = game()
    assert sorted(s.sector_order) == [1, 2, 3, 4] and len(s.sectors) == 8
    boards = {b["id"]: [x["name"] for x in b["stars"]] for b in tables.stars()["boards"]}
    for k, board_id in enumerate(s.sector_order):
        assert [s.sectors[2 * k].star, s.sectors[2 * k + 1].star] == boards[board_id]
    assert all(4 <= x.capacity <= 6 and x.data_remaining == x.capacity for x in s.sectors)
    assert sorted(x.color for x in s.sectors) == ["black", "black", "blue", "blue", "red", "red", "yellow", "yellow"]


def test_species_tiles_and_stacks() -> None:
    """SETUP-11, SETUP-16, SETUP-19."""
    s = game()
    assert len({x.species for x in s.species}) == 2 and not any(x.discovered for x in s.species)
    assert len(s.tech_stacks) == 12 and all(
        sorted(t.tiles) == ["card", "energy", "publicity", "vp3"] and t.two_point_tile for t in s.tech_stacks
    )
    assert [g.tile for g in s.gold_tiles] == ["Tech", "Mission", "Income", "Other"] and all(g.side in "AB" for g in s.gold_tiles)


def test_reproducible_from_seed() -> None:
    """A-004: the same options give the same game; a different seed gives a different one."""
    assert game(seed=5).model_dump() == game(seed=5).model_dump()
    assert game(seed=5).model_dump() != game(seed=6).model_dump()


def test_each_player_must_tuck_a_card_first() -> None:
    """SETUP-36: one setup decision per player, in turn order."""
    s = game(3)
    assert [d.kind for d in s.pending] == ["setup_tuck"] * 3
    assert [d.player for d in s.pending] == [(s.start_player + k) % 3 for k in range(3)]
