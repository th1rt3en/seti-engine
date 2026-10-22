"""The games of people, from the archive, as examples (dataset.py): which games count, with what weight, and the mix with the games of bots."""

import json
import random
from pathlib import Path
from typing import Any

from seti_engine.models import Options

from seti_ai import arena, bots, dataset
from seti_ai.bundle_data import Examples, examples_from_log

SEED = 5


def a_game() -> arena.GameResult:
    return arena.play_game([bots.heuristic(), bots.heuristic()], SEED, random.Random(SEED), {})


GAME = a_game()
SCORES = [int(s) for s in GAME.scores]


def replay_file(
    model_seat: int | None = None, consent: bool = True, status: str = "finished", reason: str = "completed", scores: list[int] | None = None
) -> dict[str, Any]:
    scores = scores if scores is not None else SCORES
    seats = [{"seat": i, "userId": f"u{i}", "name": f"P{i}", "registered": True} for i in range(2)]
    if model_seat is not None:
        seats[model_seat] = {"seat": model_seat, "userId": "bot:v001:0", "name": "AI v001", "registered": False, "bot": {"model": "v001"}}
    header: dict[str, Any] = {"id": "g1", "options": Options(players=2, seed=SEED).model_dump(), "seats": seats, "rngEncoding": "exact"}
    if model_seat is not None and consent:
        header["consent"] = {"by": "u0", "at": 1}
    ranking = [{"seat": i, "rank": 1, "score": s} for i, s in enumerate(scores)]
    return {
        "header": header,
        "actions": [{"seq": i, "seat": 0, "action": a, "at": 0, "events": []} for i, a in enumerate(GAME.actions)],
        "result": {"status": status, "result": {"reason": reason, "ranking": ranking}},
    }


def one(file: dict[str, Any]) -> Examples | str:
    return dataset.examples_of(dataset.parse(file))


def test_a_game_of_people_teaches_the_value_of_both_seats_and_does_not_imitate_the_moves() -> None:
    got = one(replay_file())
    assert isinstance(got, Examples) and got.finished
    plain = examples_from_log(Options(players=2, seed=SEED), GAME.actions)
    assert len(got.value) == len(plain.value) and {v.weight for v in got.value} == {1.0}
    assert got.policy == [], "the exact moves of the people are not policy examples"


def test_the_moves_of_people_can_be_imitated_with_a_weight_if_asked_for() -> None:
    got = dataset.examples_of(dataset.parse(replay_file()), imitate=0.5)
    assert isinstance(got, Examples)
    plain = examples_from_log(Options(players=2, seed=SEED), GAME.actions)
    assert len(got.policy) == len(plain.policy) and {p.weight for p in got.policy} == {0.5}


def test_a_game_with_the_model_counts_whoever_won_and_the_models_own_moves_are_never_imitated() -> None:
    if SCORES[0] == SCORES[1]:
        return
    for model_seat in (SCORES.index(min(SCORES)), SCORES.index(max(SCORES))):  # the model lost, the model won
        got = dataset.examples_of(dataset.parse(replay_file(model_seat=model_seat)), imitate=1.0)
        assert isinstance(got, Examples)
        plain = examples_from_log(Options(players=2, seed=SEED), GAME.actions)
        assert len(got.value) == len(plain.value), "the positions of both seats give value labels"
        assert 0 < len(got.policy) < len(plain.policy), "only the person's moves, not the model's"


def test_a_game_with_the_model_and_without_the_hosts_agreement_is_never_used() -> None:
    loser = SCORES.index(min(SCORES))
    assert one(replay_file(model_seat=loser, consent=False)) == "an AI without the host's agreement"


def test_a_game_that_was_not_played_to_the_end_is_skipped() -> None:
    assert one(replay_file(reason="resigned")) == "not played to the end"
    assert one(replay_file(status="cancelled")) == "not played to the end"
    f = replay_file()
    f["result"] = None
    assert one(f) == "not played to the end"


def test_a_log_that_the_engine_cannot_replay_is_skipped_and_counted() -> None:
    f = replay_file()
    f["actions"][3]["action"] = {"type": "no_such_move"}
    assert one(f) == "cannot be replayed"


def test_the_games_under_a_folder_are_found_in_both_forms(tmp_path: Path) -> None:
    f = replay_file()
    (tmp_path / "2026" / "10" / "21" / "g1").mkdir(parents=True)
    (tmp_path / "2026" / "10" / "21" / "g1" / "replay.json").write_text(json.dumps(f), encoding="utf-8")
    g2 = tmp_path / "2026" / "10" / "22" / "g2"
    (g2 / "actions").mkdir(parents=True)
    (g2 / "header.json").write_text(json.dumps(f["header"]), encoding="utf-8")
    (g2 / "result.json").write_text(json.dumps(f["result"]), encoding="utf-8")
    for e in f["actions"]:
        (g2 / "actions" / f"{e['seq']:07d}.json").write_text(json.dumps(e), encoding="utf-8")
    (tmp_path / "2026" / "10" / "23").mkdir()
    (tmp_path / "2026" / "10" / "23" / "replay.json").write_text("not json", encoding="utf-8")
    data, stats = dataset.load_examples(tmp_path, imitate=1.0)
    assert (stats.games, stats.used, stats.skipped) == (3, 2, {"unreadable": 1})
    assert len(data.policy) == 2 * len(examples_from_log(Options(players=2, seed=SEED), GAME.actions).policy)
    assert "3 games, 2 used" in str(stats)


def test_the_mix_has_about_the_share_of_the_games_of_people() -> None:
    bots_data = examples_from_log(Options(players=2, seed=SEED), GAME.actions)
    people = Examples()
    people.policy = bots_data.policy[:50]
    people.value = bots_data.value[:5]
    out = dataset.mix(bots_data, people, 0.25)
    n_b = len(bots_data.policy)
    assert len(out.policy) == n_b + int(n_b * 0.25 / 0.75), "the games of people are a quarter of the data"
    assert out.policy[:n_b] == bots_data.policy, "the games of bots stay as they are"
    assert dataset.mix(bots_data, people, 0.0).policy == bots_data.policy
    assert len(dataset.mix(bots_data, Examples(), 0.5).policy) == n_b, "no games of people: the bots alone"
    few = dataset.mix(bots_data, people, 0.9, max_repeat=2)
    assert len(few.policy) == n_b + 100, "repeated at most twice"
