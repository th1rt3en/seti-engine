"""Loads the confirmed board and card data that ships inside the package (see tools/engine/sync_data.py)."""

from __future__ import annotations

import json
from functools import cache
from importlib import resources
from typing import Any


@cache
def load(name: str) -> Any:
    with resources.files("seti_engine.data").joinpath(name).open(encoding="utf-8") as f:
        return json.load(f)


def solar() -> dict[str, Any]:
    out: dict[str, Any] = load("solar-system.json")
    return out


def cards() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = load("cards.json")
    return out


def stars() -> dict[str, Any]:
    out: dict[str, Any] = load("stars.json")
    return out


def planets() -> dict[str, Any]:
    out: dict[str, Any] = load("planets.json")
    return out


def rival_cards() -> dict[str, dict[str, Any]]:
    """The 19 rival action cards by id (S.1 to S.19)."""
    data: dict[str, Any] = load("rival-action-cards.json")
    return {c["id"]: c for c in data["cards"]}


def solo_boards() -> dict[str, Any]:
    out: dict[str, Any] = load("solo-boards.json")
    return out


def objectives() -> dict[str, Any]:
    out: dict[str, Any] = load("objectives.json")
    return out


def planet_info(name: str) -> dict[str, Any]:
    """Rewards and moons of a planet; 'Oumuamua is a planet once discovered (ALIEN-OUM-05)."""
    if name.upper() == "OUMUAMUA":
        pl = alien_boards()["oumuamua"]["planet_like"]
        info: dict[str, Any] = {
            "first_orbit": pl["first_orbiter"],
            "orbit": pl["orbit"],
            "land": pl["land"],
            "first_land_data": pl["first_lander_data"],
            "moons": {},
        }
        return info
    out: dict[str, Any] = planets()["planets"][name.upper()]
    return out


def alien_boards() -> dict[str, Any]:
    out: dict[str, Any] = load("alien-boards.json")
    return out


def tech_board() -> dict[str, Any]:
    out: dict[str, Any] = load("tech-board.json")
    return out


def player_board() -> dict[str, Any]:
    out: dict[str, Any] = load("player-board.json")
    return out


def gold_tiles() -> dict[str, Any]:
    out: dict[str, Any] = load("gold-tiles.json")
    return out
