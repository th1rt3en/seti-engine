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


@cache
def cards() -> dict[str, dict[str, Any]]:
    """The static facts of the cards. The quick start cards that are tucked for income (SR.15, SR.16; EXP-QS-02) are in it too, with deck
    "quick" so that no deck is built from them, because a tucked card is looked up like any other for its income."""
    out: dict[str, dict[str, Any]] = dict(load("cards.json"))
    for pc in load("promo-set-2.json")["cards"]:  # promo set 2 (PROMO-04), a game setting like promo set 1
        out[pc["id"]] = {
            "name": pc["name"],
            "deck": "promo2",
            "cost": pc["cost"],
            "income": pc["income"],
            "sector": pc["sector"],
            "species": None,
            "free": pc["free"],
        }
    for dc in deck()["cards"]:  # the 42 cards that join the main deck (EXP-03)
        out[dc["id"]] = {
            "name": dc["name"],
            "deck": "expansion",
            "cost": dc["cost"],
            "income": dc["income"],
            "sector": dc["sector"],
            "species": None,
            "free": dc["free"],
        }
    for ac in amoeba()["cards"]:  # the Amoeba species deck (EXP-AMO-01)
        out[ac["id"]] = {
            "name": f"Amoeba {ac['printed']}",
            "deck": "alien",
            "cost": ac["cost"],
            "income": ac["income"],
            "sector": ac["sector"],
            "species": "amoeba",
            "free": ac["free"],
        }
    for gc in glyphids()["cards"]:  # the Glyphids species deck (EXP-GLY-01); the corner gives the resource of a glyph if it is deciphered
        out[gc["id"]] = {
            "name": f"Glyphids {gc['printed']}",
            "deck": "alien",
            "cost": gc["cost"],
            "income": gc["income"],
            "sector": gc["sector"],
            "species": "glyphids",
            "free": [[f"glyph:{gc['corner']}", 1]],
        }
    for sc in arkhos()["security"]:  # the Arkhos security cards (EXP-ARK-03): discarded for a minor, played for a major exploration reward
        out[sc["id"]] = {
            "name": sc["name"],
            "deck": "alien",
            "cost": 2,
            "income": sc["income"],
            "sector": sc["sector"],
            "species": "arkhos",
            "free": [["explore_minor", 1]],
        }
    for qid, q in quick_start_cards().items():
        if q["income_increase"]:
            out[qid] = {
                "name": f"Quick start {qid}",
                "deck": "quick",
                "cost": 0,
                "income": q["income_increase"],
                "sector": None,
                "species": None,
                "free": [],
            }
    return out


def glyphids() -> dict[str, Any]:
    out: dict[str, Any] = load("expansion-glyphids.json")
    return out


def deck() -> dict[str, Any]:
    out: dict[str, Any] = load("expansion-deck.json")
    return out


def amoeba() -> dict[str, Any]:
    out: dict[str, Any] = load("expansion-amoeba.json")
    return out


def arkhos() -> dict[str, Any]:
    out: dict[str, Any] = load("expansion-arkhos.json")
    return out


def stars() -> dict[str, Any]:
    out: dict[str, Any] = load("stars.json")
    return out


def planets() -> dict[str, Any]:
    out: dict[str, Any] = load("planets.json")
    return out


def organizations() -> dict[str, dict[str, Any]]:
    """The 11 organizations of the expansion by id (docs/spec/expansion-data.md, owner check pending)."""
    out: dict[str, dict[str, Any]] = {o["id"]: o for o in load("expansion-organizations.json")["organizations"]}
    return out


def quick_start_cards() -> dict[str, dict[str, Any]]:
    """The 21 quick start cards by id, SR.1 to SR.21 (docs/spec/expansion-data.md, owner check pending)."""
    out: dict[str, dict[str, Any]] = {q["id"]: q for q in load("expansion-quick-start.json")["quick_start_cards"]}
    return out


def rival_cards() -> dict[str, dict[str, Any]]:
    """The 19 rival action cards by id (S.1 to S.19), and the rival cards of the expansion (SE.*, EXP-SOLO-02)."""
    data: dict[str, Any] = load("rival-action-cards.json")
    out = {c["id"]: c for c in data["cards"]}
    out.update({c["id"]: c for c in expansion_solo()["rival_cards"]})
    return out


def expansion_solo() -> dict[str, Any]:
    """The long-term objective tiles and the rival cards of the expansion (EXP-SOLO-*)."""
    out: dict[str, Any] = load("expansion-solo.json")
    return out


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
    """The boards of the species: the five of the base game and those of the expansion (EXP-03)."""
    out: dict[str, Any] = {
        **load("alien-boards.json"),
        "arkhos": arkhos()["board"],
        "glyphids": glyphids()["board"],
        "amoeba": amoeba()["board"],
    }
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
