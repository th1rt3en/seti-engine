"""The promotion gate: when the network that is being trained becomes the new champion (a saved version).

A candidate is promoted only when it
1. beats the current champion head to head: `H2H_GAMES` games, seats swapped, both playing their best moves, the candidate winning at least `MIN_WIN_RATE`
   of them (a tie counts half) and scoring more points on average; and
2. does not fall behind on a fixed yardstick: its mean own score against heuristic bot version 3 is not lower than the champion's by more than
   `BENCH_TOLERANCE` points.

Beating the previous champion alone says little: two weak versions can keep beating each other while the scores stay low (or fall). So the mean final scores
are written down at every evaluation (`metrics.jsonl`) next to `REFERENCE_SCORE`, the average of an advanced human player (the owner's experience), and a
promotion that happens while the scores are far below it is flagged. Promotion only saves a version for testing: the owner approves a version by hand.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

H2H_GAMES = 100
MIN_WIN_RATE = 0.55
BENCH_TOLERANCE = 5.0
REFERENCE_SCORE = 250.0  # what an advanced player scores on average, in a 2-player game
LOW_SHARE = 0.5  # a promotion with a mean score below this share of the reference is flagged


@dataclass
class Decision:
    promote: bool
    reason: str


def decide(champion: dict[str, Any] | None, h2h: dict[str, Any] | None, bench: float) -> Decision:
    """`champion`: {"bench": its mean score against heuristic v3, ...} or None; `h2h`: {"win_rate", "agent_score", "bot_score", "games"} of the candidate
    against the champion; `bench`: the candidate's mean score against heuristic v3."""
    if champion is None:
        return Decision(True, "the first version: there is no champion yet")
    if h2h is None:
        return Decision(False, "no head-to-head result")
    if h2h["win_rate"] < MIN_WIN_RATE:
        return Decision(False, f"wins {h2h['win_rate']:.0%} of {h2h['games']} games against the champion, {MIN_WIN_RATE:.0%} are needed")
    if h2h["agent_score"] <= h2h["bot_score"]:
        return Decision(False, f"scores {h2h['agent_score']} against the champion's {h2h['bot_score']}: not more")
    if bench < float(champion["bench"]) - BENCH_TOLERANCE:
        return Decision(False, f"scores {bench} against heuristic v3, the champion {champion['bench']}: it has fallen behind on the yardstick")
    return Decision(True, f"wins {h2h['win_rate']:.0%} of {h2h['games']} games against the champion ({h2h['agent_score']} against {h2h['bot_score']})")


def share_of_reference(score: float) -> str:
    return f"{score / REFERENCE_SCORE:.0%} of the {REFERENCE_SCORE:.0f} of an advanced player"


def is_low(score: float) -> bool:
    return score < LOW_SHARE * REFERENCE_SCORE


def log_metrics(root: Path, record: dict[str, Any]) -> None:
    """Append one line to `metrics.jsonl` (one JSON object per line: a round of training or an evaluation)."""
    root.mkdir(parents=True, exist_ok=True)
    with (root / "metrics.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "reference_score": REFERENCE_SCORE, **record}) + "\n")
