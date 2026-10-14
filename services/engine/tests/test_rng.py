"""RNG: deterministic and unbiased enough (CLAUDE.md rule 4, A-004)."""

from types import SimpleNamespace

from seti_engine import rng

KNOWN = [12035550249420947055, 12935080325729570654]


def make(seed: int = 1) -> SimpleNamespace:
    return SimpleNamespace(rng_state=rng.seed_state(seed))


def test_same_seed_same_sequence() -> None:
    a, b = make(7), make(7)
    assert [rng.next_u64(a) for _ in range(20)] == [rng.next_u64(b) for _ in range(20)]


def test_different_seeds_differ() -> None:
    assert rng.next_u64(make(1)) != rng.next_u64(make(2))


def test_known_vector() -> None:
    # pins the algorithm so a change of generator is a deliberate, visible decision
    s = make(0)
    assert [rng.next_u64(s) for _ in range(2)] == KNOWN


def test_below_range_and_coverage() -> None:
    s = make(3)
    seen = {rng.below(s, 6) for _ in range(500)}
    assert seen == set(range(6))


def test_shuffle_is_a_permutation_and_reproducible() -> None:
    items = list(range(52))
    a, b = make(5), make(5)
    x, y = rng.shuffled(a, items), rng.shuffled(b, items)
    assert x == y and sorted(x) == items and x != items
