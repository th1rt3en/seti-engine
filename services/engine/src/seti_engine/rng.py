"""Deterministic random numbers (spec: A-004, CLAUDE.md rule 4).

All randomness in a game comes from one 64-bit state stored in the game state (`rng_state`). The generator is SplitMix64, which is
simple, fast and has no hidden state, so a game is reproducible from its seed and its action log in any language.
"""

from __future__ import annotations

from collections.abc import MutableSequence
from typing import Protocol

_MASK = (1 << 64) - 1
_GOLDEN = 0x9E3779B97F4A7C15


class HasRng(Protocol):
    rng_state: int


def seed_state(seed: int) -> int:
    """Initial rng state for a game seed (mixed once so small seeds are not correlated)."""
    z = (seed + _GOLDEN) & _MASK
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
    return z ^ (z >> 31)


def next_u64(s: HasRng) -> int:
    s.rng_state = (s.rng_state + _GOLDEN) & _MASK
    z = s.rng_state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
    return z ^ (z >> 31)


def below(s: HasRng, n: int) -> int:
    """Uniform integer in [0, n) without modulo bias."""
    if n <= 0:
        raise ValueError("n must be positive")
    limit = (_MASK + 1) - ((_MASK + 1) % n)
    while True:
        x = next_u64(s)
        if x < limit:
            return x % n


def shuffle[T](s: HasRng, items: MutableSequence[T]) -> None:
    """In-place Fisher-Yates shuffle."""
    for i in range(len(items) - 1, 0, -1):
        j = below(s, i + 1)
        items[i], items[j] = items[j], items[i]


def shuffled[T](s: HasRng, items: list[T]) -> list[T]:
    out = list(items)
    shuffle(s, out)
    return out


def choice[T](s: HasRng, items: list[T]) -> T:
    return items[below(s, len(items))]
