"""The views that the networks are given: the engine's projection, with the mark of the moves that cannot be taken back (`irreversible`) left out when the
network was made without it. That mark is found by trying each legal move on a copy of the game: about 95% of the time of a view, and the tree search
makes thousands of views for a turn (docs/AI-MCTS.md). The older networks (Alpha) have it as an input and keep it; the Beta line does not.

`IRREVERSIBLE` is the setting of this process, for the code that has no network at hand (the arena, making examples from a log): a training run sets it
from the network it trains (`set_irreversible`), and a brain asks its own network (`NetConfig.irreversible`).
"""

from __future__ import annotations

from seti_engine import projection
from seti_engine.models import GameState
from seti_engine.projection import View

IRREVERSIBLE = True


def set_irreversible(on: bool) -> None:
    global IRREVERSIBLE
    IRREVERSIBLE = on


def project(state: GameState, viewer: int | None, previews: bool = False, irreversible: bool | None = None) -> View:
    return projection.project(state, viewer, previews, IRREVERSIBLE if irreversible is None else irreversible)
