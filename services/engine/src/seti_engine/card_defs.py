"""Structured effects of the 138 base-game cards, transcribed from the card art and checked against docs/spec/data/card-definitions.json.

Each card has `fx` (steps run in order when the card is played as the main action, CARD-01), and optionally `mission` (a quick mission
(CARD-11) or a triggerable mission (CARD-12)) or `end` (end-of-game scoring, CARD-20). `todo` marks a card whose effect the engine cannot
run yet, so it cannot be played. The format is documented in cards.py. FAQ-C* notes refer to docs/spec/faq.md.
"""

from __future__ import annotations

from typing import Any

Step = dict[str, Any]


def R(t: str, n: int = 1, **kw: Any) -> Step:
    return {"t": t, "n": n, **kw}


def vp(n: int) -> Step:
    return R("vp", n)


def pub(n: int) -> Step:
    return R("publicity", n)


def data(n: int) -> Step:
    return R("data", n)


def energy(n: int) -> Step:
    return R("energy", n)


def credit(n: int) -> Step:
    return R("credit", n)


def move(n: int) -> Step:
    return R("move", n)


def card(n: int = 1) -> Step:  # a card from the row or the deck
    return R("card_any", n)


def rnd(n: int = 1) -> Step:  # random cards from the deck
    return R("card_random", n)


LAUNCH = R("launch")
ROT = R("rotate")
TUCK = R("tuck")


def research(cat: str, **kw: Any) -> Step:
    return R("research", cat=cat, **kw)


def sig_star(star: str, n: int) -> Step:
    return R("sig_star", n, star=star)


def sig_color(color: str, n: int = 1) -> Step:
    return R("signal_color", n, color=color)


def sig_probe(n: int, nbrs: bool = False, nodata: bool = False) -> Step:
    return R("sig_probe", n, nbrs=nbrs, nodata=nodata)


def sig_planet(planet: str, n: int) -> Step:
    return R("sig_planet", n, planet=planet)


def row_scan(n: int) -> list[Step]:
    return [R("row_scan", n), R("refill_row")]  # FAQ-C045: discard all the row cards for signals first, then refill


def scan_free(**kw: Any) -> Step:
    return R("scan_free", **kw)


def trace(kind: str, n: int = 1, **kw: Any) -> Step:
    return R("trace", n, kind=kind, **kw)


def when(cond: dict[str, Any], *then: Step) -> Step:
    return R("if", cond=cond, then=list(then))


def watch(w: dict[str, Any]) -> Step:
    return R("watch", w=w)


def flyby(n: int, planet: str, points: int) -> list[Step]:
    return [move(n), watch({"k": "visit", "planet": planet, "r": [vp(points)]})]  # FAQ-C020: once per turn, only later visits


# --- mission conditions ------------------------------------------------------------------------------------------------------------


def orbland(
    planet: str | None = None, n: int = 1, landers_only: bool = False, moons: bool = True, orbiters_only: bool = False
) -> dict[str, Any]:
    return {"c": "orbland", "planet": planet, "n": n, "landers_only": landers_only, "moons": moons, "orbiters_only": orbiters_only}


def wins(color: str | None, n: int) -> dict[str, Any]:
    return {"c": "wins", "color": color, "n": n}


def traces(kind: str, n: int) -> dict[str, Any]:
    return {"c": "traces", "kind": kind, "n": n}


def each_species(kind: str) -> dict[str, Any]:
    return {"c": "each_species", "kind": kind}


def quick(cond: dict[str, Any], *r: Step) -> dict[str, Any]:
    return {"kind": "quick", "cond": cond, "r": list(r)}


def circle(on: dict[str, Any], *r: Step) -> dict[str, Any]:
    return {"on": on, "r": list(r)}


# the cards whose flavor text names Mars (confirmed by the owner, A-027): #13, #14, #22, #34, #76, #84, #85, #119, ET.4, SA.31
MARS_FLAVOR = frozenset({"13", "14", "22", "34", "76", "84", "85", "119", "ET.4", "SA.31"})
# SE EN 02: an orbit or a landing at Mars (or its moons), or playing a card that names Mars in its flavor text
MARS_TRIGGER = {"any": [{"e": "orbit", "planet": "mars"}, {"e": "land", "planet": "mars"}, {"e": "play_mars"}]}


def trig(*circles: dict[str, Any]) -> dict[str, Any]:
    return {"kind": "trigger", "circles": list(circles)}


def visit(planet: str) -> dict[str, Any]:
    return {"e": "visit", "planet": planet}  # planet "*" = any planet except Earth


def tech_on(cat: str) -> dict[str, Any]:
    return {"e": "tech", "cat": cat}


def end(what: str, n: int, **kw: Any) -> dict[str, Any]:
    return {"what": what, "n": n, **kw}


# --- the cards ---------------------------------------------------------------------------------------------------------------------

CARDS: dict[str, dict[str, Any]] = {
    "1": {"mission": trig(circle(visit("jupiter"), data(1)), circle(visit("saturn"), vp(4)))},
    "2": {"mission": trig(circle(visit("mercury"), rnd(1)), circle(visit("venus"), pub(1)))},
    "3": {"mission": trig(circle(visit("uranus"), energy(1)), circle(visit("neptune"), credit(1)))},
    "4": {"mission": trig(circle(visit("venus"), pub(1)), circle(visit("jupiter"), data(1)))},
    "5": {"fx": [LAUNCH, pub(1)], "mission": quick(orbland("venus"), vp(7), pub(1))},
    "6": {"fx": [LAUNCH, data(1)], "mission": quick(orbland("jupiter"), vp(7), pub(1))},
    "7": {"fx": [LAUNCH, move(1)], "mission": quick(orbland("mercury"), vp(7), pub(1))},
    "8": {"fx": [LAUNCH, card(1)], "mission": quick(orbland("saturn"), vp(6), pub(1))},
    "9": {"fx": [R("launch", 2, nolimit=True), pub(1)]},  # FAQ-C009
    "10": {"fx": [ROT, research("probe")], "mission": quick({"c": "both", "planets": ["neptune", "uranus"]}, vp(5), card(1))},
    "11": {"fx": [R("grant")]},  # FAQ-C011
    "12": {"fx": [R("land_free", any_moon=True)], "end": end("per_orbland", 3, planet="jupiter")},
    "13": {"fx": [R("land_free", bonus_vp=4, bonus_planets=["mars", "mercury"], bonus_moon=True)]},
    "14": {"fx": [pub(1), data(2)], "end": end("per_orbland", 4, planet="mars")},
    "15": {"fx": [R("remove_orbiter", r=[vp(3), data(1), card(1)])]},  # FAQ-C015, A-018
    "16": {"fx": [R("land_free", occupied=True)]},  # FAQ-C016
    "17": {"fx": [R("osiris")]},  # FAQ-C017
    "18": {"fx": [when({"c": "probe_on", "where": "asteroid"}, trace("yellow"))]},
    "19": {"fx": [move(2), watch({"k": "slingshot"})]},  # FAQ-C019
    "20": {"fx": flyby(2, "mercury", 4)},
    "21": {"fx": flyby(2, "venus", 3)},
    "22": {"fx": flyby(2, "mars", 4)},
    "23": {"fx": flyby(2, "jupiter", 4)},
    "24": {"fx": flyby(3, "saturn", 6)},
    "25": {"fx": [move(4), watch({"k": "unique_planets", "r": [vp(1)]})]},  # FAQ-C025
    "26": {"fx": [move(2), watch({"k": "ignore_asteroid"})]},  # FAQ-C026
    "27": {"fx": [move(1), sig_probe(1)]},  # FAQ-C027
    "28": {"fx": [move(1), sig_probe(2)]},
    "29": {"fx": [move(1), sig_probe(1, nbrs=True)]},
    "30": {"fx": [R("probes_sig", 3)]},  # FAQ-C030
    "31": {"fx": [LAUNCH, move(1)], "mission": quick(orbland(n=3, landers_only=True, moons=False), credit(1))},
    "32": {"fx": [sig_planet("mercury", 2)], "mission": quick(orbland("mercury"), vp(4))},
    "33": {"fx": [sig_planet("venus", 2)], "mission": quick(orbland("venus"), vp(4))},
    "34": {"fx": [sig_planet("mars", 2)], "mission": quick(orbland("mars"), vp(4))},
    "35": {"fx": [sig_planet("jupiter", 2)], "mission": quick(orbland("jupiter"), vp(4))},
    "36": {"fx": [sig_planet("saturn", 2)], "mission": quick(orbland("saturn"), vp(4))},
    "37": {"fx": [sig_star("Proxima Centauri", 2)], "mission": quick(wins("red", 2), vp(4), pub(1))},
    "38": {"fx": [sig_star("Barnard's Star", 2)], "end": end("per_wins", 3, color="red")},
    "39": {"fx": [sig_star("61 Virginis", 2)], "mission": quick(wins("yellow", 2), vp(4), pub(1))},
    "40": {"fx": [sig_star("Kepler 22", 2)], "end": end("per_wins", 3, color="yellow")},
    "41": {"fx": [sig_star("Sirius A", 2)], "mission": quick(wins("blue", 2), vp(4), pub(1))},
    "42": {"fx": [sig_star("Procyon", 2)], "end": end("per_wins", 3, color="blue")},
    "43": {"fx": [sig_star("Beta Pictoris", 1)], "mission": quick(wins("black", 1), vp(2), pub(1))},
    "44": {"fx": [sig_star("Vega", 1)], "end": end("per_wins", 3, color="black")},
    "45": {"fx": [*row_scan(2), watch({"k": "complete_sector", "r": [energy(1)]})]},  # FAQ-C045
    "46": {"fx": [*row_scan(2), watch({"k": "complete_sector", "r": [rnd(1)]})]},
    "47": {"fx": [*row_scan(2), watch({"k": "complete_sector", "r": [data(1)]})]},
    "48": {"fx": [move(1), sig_color("red")]},
    "49": {"fx": [move(1), sig_color("yellow")]},
    "50": {"fx": [*row_scan(3), R("unique_sector_vp", 2)]},  # FAQ-C050
    "51": {"fx": [data(1), scan_free()], "mission": quick({"c": "publicity", "n": 8}, vp(3), card(1))},  # FAQ-C051
    "52": {"fx": [scan_free(vp_color="red", vp=2)]},
    "53": {"fx": [scan_free(vp_color="yellow", vp=2)]},
    "54": {"fx": [scan_free(vp_color="blue", vp=2)]},
    "55": {"fx": [scan_free(), R("sig_any")]},
    "56": {"fx": [move(1), sig_color("blue")]},
    "57": {"fx": [card(1), ROT, research("telescope")]},
    "58": {"fx": [LAUNCH], "mission": quick(orbland("uranus"), vp(3), rnd(1))},  # FAQ-C058
    "59": {"fx": [energy(1), ROT, research("probe")]},
    "60": {"fx": [LAUNCH], "mission": quick(orbland("neptune"), vp(4), data(1))},
    "61": {"fx": [ROT, research("computer")], "mission": quick({"c": "score", "n": 50}, TUCK)},
    "62": {"fx": [ROT, research("telescope")], "end": end("per_traces", 2, kind="pink")},
    "63": {"fx": [ROT, research("probe")], "end": end("per_traces", 2, kind="yellow")},
    "64": {"fx": [ROT, research("computer")], "mission": quick(each_species("blue"), data(2))},
    "65": {"fx": [*row_scan(2), ROT, research("telescope")]},  # FAQ-C045: rotate and take the tech after refilling the row
    "66": {"fx": [ROT, research("telescope")], "mission": quick(each_species("pink"), vp(2), energy(1))},
    "67": {"fx": [pub(1), ROT, research("telescope"), R("hand_signals", 1)]},  # FAQ-C067
    "68": {"fx": [ROT, research("computer")], "end": end("per_traces", 2, kind="blue")},
    "69": {"fx": [data(1), ROT, research("computer")]},
    "70": {"fx": [ROT, research("computer")], "mission": quick(traces("blue", 3), vp(3), data(1))},
    "71": {"fx": [ROT, research("any", then_vp_per_tech=2)]},
    "72": {"fx": [ROT, research("any", copy_bonus=[pub(2)])]},
    "73": {"fx": [R("clean_space")]},  # FAQ-C073
    "74": {"fx": [LAUNCH, R("show_move")]},  # the player picks the cards to show from the hand (FAQ-C073)
    "75": {"fx": [R("trace_vp", vp=1)]},
    "76": {
        "mission": trig(circle(tech_on("probe"), energy(1)), circle(tech_on("telescope"), pub(1)), circle(tech_on("computer"), card(1)))
    },
    "77": {
        "fx": [pub(1)],
        "mission": trig(
            circle({"e": "trace", "kind": "pink"}, data(1)),
            circle({"e": "trace", "kind": "yellow"}, data(1)),
            circle({"e": "trace", "kind": "blue"}, data(1)),
        ),
    },
    "78": {
        "fx": [pub(1)],
        "mission": trig(circle({"e": "scan"}, data(2)), circle({"e": "scan"}, card(1)), circle({"e": "scan"}, vp(4))),  # FAQ-C078
    },
    "79": {
        "fx": [pub(1)],
        "mission": trig(circle({"e": "launch"}, credit(1)), circle({"e": "launch"}, card(1)), circle({"e": "launch"}, vp(5))),
    },
    "80": {"mission": trig(circle({"e": "launch"}, move(1)), circle({"e": "launch"}, move(1)), circle({"e": "launch"}, move(1)))},
    "81": {"fx": [research("any", copy=True)]},  # FAQ-C081
    "82": {"mission": trig(circle({"e": "orbit"}, pub(2)), circle({"e": "land"}, pub(2)))},
    "83": {"fx": [pub(1), R("sig_earth", 2)]},
    "84": {"fx": [R("remove_lander", r=[trace("yellow")])]},  # FAQ-C084, A-018
    "85": {"fx": [LAUNCH, ROT, research("probe")]},
    "86": {"fx": row_scan(1), "end": end("per_signal_sectors", 1)},
    "87": {"fx": [ROT, research("probe")], "mission": quick({"c": "probe_far", "n": 5}, vp(3), energy(1))},  # ambiguity A-017
    "88": {"fx": [sig_probe(2)], "mission": quick({"c": "sig_sectors", "n": 4}, pub(2))},  # FAQ-C088
    "89": {"fx": [rnd(3)], "mission": quick({"c": "hand_empty"}, card(1))},  # FAQ-C089
    "90": {"fx": [R("per", count="hand_income_energy", r=energy(1))]},
    "91": {"fx": [R("per", count="tucked_income_energy", r=energy(1)), R("tuck_self")]},  # FAQ-C091
    "92": {"fx": [pub(2), R("per", count="tucked_income_card", r=pub(1)), R("tuck_self")]},
    "93": {"fx": [R("per", count="tucked_income_credit", r=vp(3)), R("tuck_self")]},
    "94": {
        "fx": [pub(1)],
        "mission": trig(circle(tech_on("probe"), pub(2)), circle(tech_on("telescope"), pub(2)), circle(tech_on("computer"), pub(2))),
    },
    "95": {"fx": [pub(2)], "mission": quick({"c": "probe_on", "where": "asteroid_adjacent_earth"}, vp(5), card(1))},
    "96": {"fx": [pub(1), data(1), rnd(1)], "mission": quick(traces("yellow", 3), trace("yellow"))},
    "97": {"fx": [ROT, research("probe")], "mission": quick(each_species("yellow"), vp(2), rnd(1))},
    "98": {"fx": [R("trace_same", kind="pink")]},  # FAQ-C098
    "99": {"fx": [R("trace_same", kind="yellow")]},
    "100": {"fx": [R("trace_same", kind="blue")]},
    "101": {
        "mission": trig(
            circle({"e": "scan"}, R("signal_color", 1, color="yellow")),
            circle({"e": "scan"}, R("signal_color", 1, color="red")),
            circle({"e": "scan"}, R("signal_color", 1, color="blue")),
        )  # FAQ-C101
    },
    "102": {
        "fx": [pub(3)],
        "mission": quick({"c": "single_species_all"}, trace("any", slots="all_kinds")),
    },
    "103": {"fx": [ROT, research("telescope")], "mission": quick({"c": "wins_same", "n": 2}, vp(9))},  # FAQ-C103
    "104": {"fx": [LAUNCH], "mission": quick({"c": "probe_on", "where": "comet"}, vp(3), data(1))},
    "105": {"fx": [scan_free()], "mission": quick(traces("pink", 3), trace("pink"))},
    "106": {
        "mission": trig(
            circle({"e": "play_cost", "cost": 1}, vp(2)),
            circle({"e": "play_cost", "cost": 2}, card(1)),
            circle({"e": "play_cost", "cost": 3}, pub(2)),
        )  # FAQ-C106
    },
    "107": {
        "fx": [data(2)],
        "mission": trig(circle({"e": "trace", "kind": "blue"}, pub(2)), circle({"e": "trace", "kind": "blue"}, vp(4))),
    },
    "108": {"fx": [when({"c": "publicity", "n": 8}, trace("pink"))]},
    "109": {"fx": [energy(1), ROT, research("computer")]},
    "110": {"fx": [pub(3)]},
    "111": {"fx": [ROT, research("telescope")], "mission": quick(orbland(n=2, moons=True, orbiters_only=True), data(2))},
    "112": {"fx": [ROT, research("probe")], "mission": quick({"c": "same_planet"}, vp(3), data(1))},  # FAQ-C058
    "113": {"fx": [pub(2)], "end": end("solvay", 0)},  # FAQ-C113
    "114": {"fx": [card(1), R("hand_signals", 3)]},  # FAQ-C067
    "115": {"fx": [R("sig_any")], "mission": quick({"c": "techs", "cat": "telescope", "n": 3}, data(1))},
    "116": {
        "mission": trig(
            circle({"e": "signal", "color": "yellow"}, move(1)),
            circle({"e": "signal", "color": "red"}, move(1)),
            circle({"e": "signal", "color": "blue"}, move(1)),
        )  # FAQ-C116
    },
    "117": {"fx": [LAUNCH], "mission": trig(circle({"e": "orbit_or_land"}, LAUNCH), circle({"e": "orbit_or_land"}, energy(1)))},  # FAQ-C117
    "118": {"fx": [sig_probe(3, nodata=True)]},  # FAQ-C118
    "119": {"fx": [ROT, research("computer"), R("per", count="publicity", r=vp(1))]},  # FAQ-C119
    "120": {"fx": [R("lagrange")]},  # FAQ-C120
    "121": {"fx": [data(3), ROT, research("computer")]},
    "122": {"fx": [R("deck_signals", 3)]},  # FAQ-C122
    "123": {"fx": [move(1), watch({"k": "visit_asteroids", "r": [data(1)]})]},  # FAQ-C123
    "124": {"fx": [move(2), watch({"k": "visit_comet", "r": [vp(4)]})]},
    "125": {"fx": [move(1), watch({"k": "same_ring", "r": [vp(3), pub(1)]})]},  # FAQ-C125
    "126": {"fx": [ROT, research("probe_telescope")], "end": end("per_techs", 2, cat="computer")},  # FAQ-C126
    "127": {"fx": [pub(2)], "end": end("probe_on_asteroid", 13)},  # FAQ-C127
    "128": {"mission": trig(circle(visit("*"), energy(1)), circle(visit("*"), data(1)), circle(visit("*"), move(1)))},  # FAQ-C128
    "129": {"mission": trig(*[circle({"e": "visit_asteroids", "own_turn": True}, data(1)) for _ in range(3)])},  # FAQ-C123
    "130": {"fx": [LAUNCH]},
    "131": {"fx": [card(1)], "mission": trig(circle(tech_on("telescope"), pub(1)), circle({"e": "scan"}, data(1)))},
    "132": {"fx": [LAUNCH, pub(2)], "mission": quick(orbland(n=5), vp(3), credit(1))},
    "133": {"fx": [LAUNCH, R("optimal")]},  # FAQ-C133
    "134": {"fx": [sig_probe(1)], "mission": quick({"c": "sig_sectors", "n": 4}, pub(2))},
    "135": {"fx": [pub(1), scan_free()]},
    "136": {"fx": [R("sig_each_color", nodata=True)]},  # FAQ-C118
    "137": {"fx": [data(2)]},
    "138": {
        "mission": trig(
            circle({"e": "discard_free", "corner": "publicity"}, pub(1)),
            circle({"e": "discard_free", "corner": "data"}, data(1)),
            circle({"e": "discard_free", "corner": "move"}, move(1)),
        )  # FAQ-C138
    },
}


# --- alien cards (ET.1 to ET.40; the Exertian cards ET.41 to ET.55 are played by the species rules) ------------------------------------


def species_traces(species: str, kind: str, n: int) -> dict[str, Any]:
    return {"c": "species_traces", "species": species, "kind": kind, "n": n}


def species_all(species: str) -> dict[str, Any]:
    return {"c": "species_all", "species": species}


def deliver(dest: str, *r: Step, twice: bool = False) -> dict[str, Any]:
    """ALIEN-MASC-04: a mission completed by delivering a sample capsule to Earth or Mars."""
    return {"kind": "deliver", "dest": dest, "r": list(r), "twice": twice}


def land_collect(**kw: Any) -> Step:
    return R("land_free", collect=True, **kw)


def message(*green: Step) -> list[Step]:
    """ALIEN-CEN-02: place the marker 15 points ahead; when reached, the green part resolves."""
    return [R("message")]


def exo(n: int = 1) -> Step:
    return R("exofossil", n)


ANY = "*"  # a trigger circle that any kind or category satisfies

ALIEN_CARDS: dict[str, dict[str, Any]] = {
    # Mascamites
    "ET.1": {"fx": [move(1), land_collect()], "mission": deliver("earth", data(2))},
    "ET.2": {"fx": [land_collect(any_moon=True)], "mission": deliver("earth", vp(3), data(3))},
    "ET.3": {"fx": [R("orbit_land_free", collect=True)], "mission": deliver("earth", vp(3), credit(1))},
    "ET.4": {"fx": [land_collect()], "mission": deliver("mars", vp(2), card(1))},
    "ET.5": {"fx": [R("sample_peek", probe=True)], "end": end("per_species_traces", 1, species="mascamites")},
    "ET.6": {"fx": [land_collect(any_moon=True)], "mission": deliver("earth", vp(6), pub(2))},
    "ET.7": {"fx": [land_collect()], "mission": deliver("earth", twice=True)},
    "ET.8": {"fx": [pub(1), ROT, research("probe")], "mission": quick(species_traces("mascamites", "yellow", 2), R("sample_peek"))},
    "ET.9": {"fx": [pub(1), ROT, research("telescope")], "mission": quick(species_traces("mascamites", "pink", 2), R("sample_peek"))},
    "ET.10": {"fx": [pub(1), ROT, research("computer")], "mission": quick(species_traces("mascamites", "blue", 2), R("sample_peek"))},
    # Anomalies
    "ET.11": {"fx": [LAUNCH, when({"c": "anomaly_at_earth"}, move(1))]},
    "ET.12": {"fx": [move(5), watch({"k": "no_pub_move"})]},
    "ET.13": {
        "fx": [pub(1)],
        "mission": trig(circle(tech_on(ANY), energy(1)), circle(tech_on(ANY), card(1)), circle(tech_on(ANY), vp(3))),
    },
    "ET.14": {"fx": [scan_free(), R("sig_next_anomaly")]},
    "ET.15": {"fx": [R("part_of_life")]},
    "ET.16": {"fx": [R("take_row_all")]},
    "ET.17": {"fx": [R("next_anomaly_reward")], "mission": quick(species_all("anomalies"), vp(3), pub(2))},
    "ET.18": {"fx": [ROT, research("any")]},
    "ET.19": {"fx": [trace("any")]},
    "ET.20": {"fx": [R("sig_any"), R("anomaly_signal_vp")]},
    # 'Oumuamua
    "ET.21": {"fx": [scan_free(vp_tile=2)], "mission": quick({"c": "paid_space"}, data(1))},
    "ET.22": {
        "fx": [scan_free(exo_if_tile=True)],
        "mission": quick(orbland("oumuamua", landers_only=True, moons=False), vp(4)),
    },
    "ET.23": {"fx": [R("signal_oumuamua")], "mission": quick({"c": "exofossils", "n": 3}, R("exofossil_pay", 2), vp(11))},
    "ET.24": {
        "fx": [sig_color("yellow"), sig_color("red"), sig_color("blue"), R("optional", exo=1, r=[R("signal_any")])],
        "end": end("per_species_traces", 1, species="oumuamua"),
    },
    "ET.25": {"fx": [R("optional", exo=1, r=[move(2)], repeat=True), R("land_free")]},
    "ET.26": {"fx": [LAUNCH, exo(1)]},
    "ET.27": {
        "fx": [move(4), watch({"k": "visit", "planet": "oumuamua", "r": [exo(1)]})],
        "mission": quick({"c": "tile_marker"}, exo(1)),
    },
    "ET.28": {"fx": [ROT, research("computer"), R("optional", exo=1, r=[data(1)])]},
    "ET.29": {
        "fx": [exo(1)],
        "mission": trig(
            circle({"e": "trace", "kind": ANY}, data(1)),
            circle({"e": "trace", "kind": ANY}, pub(1)),
            circle({"e": "trace", "kind": ANY}, vp(3)),
        ),
    },
    "ET.30": {
        "fx": [R("land_free", bonus_vp=3, bonus_planets=["oumuamua"])],
        "mission": quick(species_all("oumuamua"), exo(1)),
    },
    # Promo cards (PLAN.md D23, PROMO-01 to PROMO-03)
    "SE_EN_01": {"fx": [R("pluto")], "keep": True},
    "SE_EN_02": {"mission": trig(circle(MARS_TRIGGER, pub(2)), circle(MARS_TRIGGER, vp(5)))},
    # Promo set 2 (PROMO-04): the memory of SE EN 03 between games is not implemented (A-035, owner 2026-10-15)
    "SE_EN_03": {"fx": [LAUNCH, R("signal_token")]},
    "SE_DE_04": {"fx": [LAUNCH, R("dlr")]},
    # Centaurians (they cost energy; the green part resolves when the message marker is reached)
    "ET.31": {"fx": [*message(), LAUNCH], "green": [R("tuck_self")]},
    "ET.32": {"fx": [*message(), data(2)], "green": [R("tuck_self")]},
    "ET.33": {"fx": [*message(), pub(1), credit(1)], "green": [R("tuck_self")]},
    "ET.34": {"fx": [*message(), rnd(1)], "green": [trace("pink")]},
    "ET.35": {"fx": [*message(), data(1)], "green": [trace("yellow")]},
    "ET.36": {"fx": [*message(), pub(2)], "green": [trace("blue")]},
    "ET.37": {"fx": [*message(), card(1)], "green": [credit(1), trace("any")]},
    "ET.38": {"fx": [*message(), ROT, research("computer")], "green": [R("tuck_self")]},
    "ET.39": {"fx": [*message(), ROT, research("telescope")], "green": [R("tuck_self")]},
    "ET.40": {"fx": [*message(), R("sig_twice", 2)], "green": [R("tuck_self")]},
}
CARDS.update(ALIEN_CARDS)


CARDS.update(
    {
        # the 42 cards of the Space Agencies main deck (EXP-03); readings of the pictures are in docs/spec/ambiguities.md (A-050)
        "SA.1": {"fx": [R("land_free", return_if_occupied=True)]},
        "SA.2": {"fx": [R("show_corner")]},
        "SA.3": {"fx": [R("signal_token", 3)]},
        "SA.4": {"fx": [R("signal_token"), move(1)]},
        "SA.5": {"fx": [data(1), move(1), when({"c": "adjacent_earth"}, R("return_card"))]},
        "SA.6": {"fx": [move(1), R("land_free", signal_here=True)]},
        "SA.7": {"fx": [ROT, research("probe")], "mission": quick({"c": "probes_planets", "n": 2}, credit(2))},
        "SA.8": {"fx": [ROT, research("computer")], "end": end("per_data", 3)},
        "SA.9": {"fx": [ROT, research("telescope")], "mission": quick(wins(None, 3), pub(3))},
        "SA.10": {"fx": [pub(10)], "end": end("per_publicity", 1)},
        "SA.11": {"fx": [LAUNCH, pub(1)], "mission": quick({"c": "probe_on", "where": "asteroid"}, vp(3), energy(2))},
        "SA.12": {"fx": [move(2), watch({"k": "planets_threshold", "n": 2, "r": [vp(3)]})]},
        "SA.13": {"fx": [scan_free(), R("signal_token")]},
        "SA.14": {"fx": [LAUNCH, pub(1), when({"c": "other_on_earth"}, R("return_card"))]},
        "SA.15": {"fx": [ROT, research("any", tile_again=True)]},
        "SA.16": {"fx": [pub(4)], "mission": quick({"c": "publicity_eq", "n": 0}, vp(2), pub(1))},
        "SA.17": {"fx": [R("paid_media")]},
        "SA.18": {"fx": [R("set_publicity", to=0), ROT, research("any", owned_by_other=True)]},
        "SA.19": {"fx": [R("remove_orbiter", r=[], probe_at_planet=True)]},
        "SA.20": {"fx": [pub(1), R("discard_corner", times=3)]},
        "SA.21": {"mission": trig(*(circle({"e": "visit", "planet": "*", "own_orbiter": True}, energy(1)) for _ in range(2)))},
        "SA.22": {"fx": [R("sig_in_rich_sector", 2, min=3)]},
        "SA.23": {"fx": [pub(1)], "mission": trig(circle({"e": "launch"}, rnd(1)), circle({"e": "orbit_or_land"}, vp(3)))},
        "SA.24": {"fx": [pub(1)], "mission": trig(*(circle({"e": "tech", "cat": "probe"}, LAUNCH) for _ in range(2)))},
        "SA.25": {"fx": [pub(1)], "mission": trig(*(circle({"e": "tech", "cat": "telescope"}, R("signal_token")) for _ in range(2)))},
        "SA.26": {"fx": [pub(1)], "mission": trig(*(circle({"e": "tech", "cat": "computer"}, data(1)) for _ in range(2)))},
        "SA.27": {"fx": [R("energy_per_probe")]},
        "SA.28": {"fx": [R("restructure")], "mission": quick({"c": "no_resources"}, pub(2), card(1))},
        "SA.29": {"fx": [R("return_mission", r=[data(2)])]},
        "SA.30": {"fx": [pub(1), R("orbit_free"), R("per", count="tech_computer", r=data(1))]},
        "SA.31": {"fx": [R("land_free")], "end": end("per_planets_two_landers", 6)},
        "SA.32": {"fx": [R("discard_hand"), pub(1), rnd(2)]},
        "SA.33": {"fx": [pub(1)], "mission": trig(circle({"e": "pass"}, LAUNCH))},
        "SA.34": {"fx": [TUCK, R("per", count="max_tech_type", r=rnd(1))]},
        "SA.35": {"fx": [R("signal_token")], "mission": quick({"c": "data_total", "n": 12}, energy(1))},
        "SA.36": {"fx": [sig_color("yellow"), sig_color("red"), sig_color("blue")]},
        "SA.37": {"fx": [R("sig_each_marked")]},
        "SA.38": {"fx": [pub(1), move(1), when({"c": "probe_shared"}, vp(3))]},
        "SA.39": {"fx": [move(2)], "end": end("per_planets_orb_or_land", 2)},
        "SA.40": {"fx": [move(5)]},
        "SA.41": {"fx": [R("signal_token"), pub(1), card(1)], "end": end("sig_all_colors", 4)},
        "SA.42": {"fx": [scan_free()], "end": end("signals_each_sector", 8)},
    }
)


def _GG(groups: list[list[str]]) -> Step:  # noqa: N802 - EXP-GLY-06: choose one group of glyph icons
    return R("glyph_group", groups=groups)


def _GL(glyph: str) -> Step:  # noqa: N802 - EXP-GLY-06
    return R("glyph_resource", glyph=glyph)


CARDS.update(
    {
        # Glyphids: icons with a "?" give the resource of that glyph when it has been deciphered (EXP-GLY-06); a group of glyphs is a choice
        "GL.1": {"fx": [_GG([["yellow", "cyan"], ["blue", "pink"]])], "end": end("glyph_most", 3)},
        "GL.2": {"fx": [_GG([["pink", "pink", "red"], ["blue", "blue", "cyan"]])]},
        "GL.3": {"mission": trig(*(circle({"e": "orbit_or_land"}, _GL(g)) for g in ("yellow", "black", "blue")))},
        "GL.4": {
            "mission": trig(
                circle({"e": "tech", "cat": "probe"}, _GL("yellow")),
                circle({"e": "tech", "cat": "telescope"}, _GL("orange")),
                circle({"e": "tech", "cat": "computer"}, _GL("red")),
            )
        },
        "GL.5": {"fx": [R("signal_token")], "mission": trig(circle({"e": "scan"}, _GL("yellow")), circle({"e": "scan"}, _GL("pink")))},
        "GL.6": {"fx": [pub(1), data(1)], "mission": trig(circle({"e": "launch"}, _GL("orange")), circle({"e": "launch"}, _GL("cyan")))},
        "GL.7": {"fx": [card(1)], "mission": trig(*(circle({"e": "trace", "kind": ANY}, _GL(g)) for g in ("red", "black", "pink")))},
        "GL.8": {"fx": [_GG([["cyan", "cyan", "red"], ["black", "black", "orange"]])]},
        "GL.9": {"fx": [_GG([["yellow", "pink"], ["blue", "orange"]])], "end": end("glyph_set", 1)},
        "GL.10": {"fx": [LAUNCH, _GL("cyan")], "mission": quick(species_all("glyphids"), _GL("red"), _GL("blue"))},
    }
)


def _AM(color: str) -> Step:  # noqa: N802 - EXP-AMO-04: one organelle of the section of that color
    return R("organelle", color=color)


CARDS.update(
    {
        # Amoeba (ET.20: the third icon is read as a pink organelle, A-049)
        "AM.11": {"fx": [card(1), _AM("pink")], "end": end("per_species_color", 2, species="amoeba", kind="pink")},
        "AM.12": {"fx": [card(1), _AM("yellow")], "end": end("per_species_color", 2, species="amoeba", kind="yellow")},
        "AM.13": {"fx": [card(1), _AM("blue")], "end": end("per_species_color", 2, species="amoeba", kind="blue")},
        "AM.14": {
            "fx": [pub(3)],
            "mission": quick({"c": "species_colors_board", "species": "amoeba"}, R("vp_empty_species_space", species="amoeba")),
        },
        "AM.15": {
            "fx": [LAUNCH, _AM("yellow")],
            "mission": trig(*(circle({"e": "trace", "kind": "blue"}, data(1)) for _ in range(2))),  # A-057: no "for this species" printed
        },
        "AM.16": {
            "fx": [data(3), _AM("blue")],
            "mission": trig(
                circle({"e": "trace", "kind": "pink"}, data(1)),  # A-057: no "for this species" printed
                circle({"e": "trace", "kind": "yellow"}, data(1)),
            ),
        },
        "AM.17": {
            "fx": [pub(1)],
            "mission": trig(
                circle({"e": "tech", "cat": "probe"}, _AM("yellow")),
                circle({"e": "tech", "cat": "telescope"}, _AM("pink")),
                circle({"e": "tech", "cat": "computer"}, _AM("blue")),
            ),
        },
        "AM.18": {
            "fx": [rnd(2)],
            "mission": trig(*(circle({"e": "trace", "kind": ANY, "species": "amoeba"}, pub(1)) for _ in range(2))),
        },
        "AM.19": {"fx": [R("amoeba_remove")]},
        "AM.20": {"fx": [R("signal_token"), pub(1), _AM("pink")]},
    }
)
for _sc in ("AK.21", "AK.22", "AK.23", "AK.24", "AK.25", "AK.26", "AK.27", "AK.28", "AK.29", "AK.30", "AK.31", "AK.32"):
    CARDS[_sc] = {"fx": [R("explore", level="major")]}  # EXP-ARK-07: played as a main action, a security card gives a major reward
