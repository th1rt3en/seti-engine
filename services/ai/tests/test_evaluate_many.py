"""The memory of the evaluation server (docs/AI-BETA-PLAN.md): the embedding of the moves does not make a tensor K times the size of its result, and the
positions are grouped by their number of moves, so that one position with hundreds of moves does not make every other position of the batch as big as itself."""

import numpy as np
import pytest
import torch

from seti_ai import features
from seti_ai.agent import LocalNet, move_embedding, new_net


def item(moves: int, tokens: int = 12, seed: int = 0) -> tuple[features.Tokens, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    per = 6
    kinds = rng.integers(0, features.ENTITY_TYPES, tokens).astype(np.int32)
    offsets = (np.arange(tokens + 1) * per).astype(np.int32)
    idx = rng.integers(0, features.OBS_DIM, tokens * per).astype(np.int32)
    val = rng.random(tokens * per).astype(np.float32)
    toks = rng.integers(0, features.TOKEN_BUCKETS, (moves, features.MAX_TOKENS)).astype(np.int32)
    toks[:, rng.integers(5, features.MAX_TOKENS)] = 0  # the padding token is in every move
    nums = rng.random((moves, features.MOVE_NUM)).astype(np.float32)
    return features.Tokens(kinds, offsets, idx, val), toks, nums


def test_the_embedding_of_a_move_is_the_sum_of_its_tokens_without_the_padding() -> None:
    torch.manual_seed(0)
    net = new_net("small")
    toks = torch.randint(0, features.TOKEN_BUCKETS, (3, 7, features.MAX_TOKENS))
    toks[:, :, 20:] = 0
    assert torch.allclose(move_embedding(net.tok, toks), net.tok(toks).sum(dim=2), atol=1e-5)


def test_positions_are_answered_in_their_order_whatever_the_groups() -> None:
    torch.manual_seed(0)
    ln = LocalNet(new_net("small"))
    items = [item(m, seed=i) for i, m in enumerate([30, 1, 7, 1, 200, 3, 12, 1, 60])]
    alone = ln.evaluate_many(items, chunk=1, slots=1)
    grouped = ln.evaluate_many(items, chunk=4, slots=100)  # a position of 200 moves is a group of its own
    together = ln.evaluate_many(items)
    for i, (a, g, t) in enumerate(zip(alone, grouped, together, strict=True)):
        assert a[0].shape == g[0].shape == t[0].shape == (items[i][1].shape[0],)
        assert np.allclose(a[0], g[0], atol=1e-4) and np.allclose(a[0], t[0], atol=1e-4)
        assert a[1] == pytest.approx(g[1], abs=1e-4) and a[1] == pytest.approx(t[1], abs=1e-4)


def test_the_groups_stay_inside_the_number_of_places() -> None:
    sizes: list[tuple[int, int]] = []
    net = new_net("small").eval()

    class Recorder:
        def __call__(self, batch: object) -> object:
            sizes.append(tuple(batch.move_mask.shape))  # type: ignore[attr-defined]
            return net(batch)

    ln = LocalNet(net)
    ln.net = Recorder()  # type: ignore[assignment]
    items = [item(m, seed=i) for i, m in enumerate([1] * 40 + [50] * 10 + [400])]
    ln.evaluate_many(items, chunk=64, slots=500)
    assert sum(b for b, _ in sizes) == len(items)
    assert all(b * m <= 500 or b == 1 for b, m in sizes)  # a position with more moves than that goes alone
    assert max(m for _, m in sizes) == 400 and [b for b, m in sizes if m == 400] == [1]


@pytest.mark.skipif(not torch.cuda.is_available(), reason="the memory of the card is measured on the card")
def test_one_position_with_many_moves_does_not_make_the_batch_big() -> None:
    torch.manual_seed(0)
    ln = LocalNet(new_net("medium").cuda())
    small = [item(1, seed=i) for i in range(63)]
    ln.evaluate_many(small + [item(20, seed=99)])  # warm up
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    before = torch.cuda.memory_allocated()
    ln.evaluate_many(small + [item(800, seed=100)])
    peak = torch.cuda.max_memory_allocated() - before
    assert peak < 400 * 2**20  # it was 2.5 GB when every position of the batch was padded to 800 moves and the tokens of all the moves were materialised
