"""Alien species: boards, alien card decks, discovery and the per-species rules.

Spec: aliens.md (ALIEN-01 to ALIEN-06, ALIEN-ANO-*, ALIEN-CEN-*), board-alien-species.md (ALIEN-DATA-10 to 13), faq.md (FAQ-40, FAQ-41).
Implemented: the boards and trace marking for all five base species, the card decks and every alien card effect, discovery, Anomalies,
Centaurian messages, Exertian cards and danger, Mascamite samples and capsules, and the 'Oumuamua tile and exofossils.
"""

from __future__ import annotations

from typing import Any

from . import effects, rewards, rival, rng, tables
from .models import Decision, GameState, PlayerState, Probe, SpeciesSlot

Events = list[dict[str, Any]]
COLORS = ("pink", "yellow", "blue")
MESSAGE_BASE = 10_000  # entries of GameState.crossed at or above this value are Centaurian message milestones (target = value - base)
CARD_MESSAGE_BASE = 30_000  # entries of GameState.crossed from this value are message cards reaching their marker (ALIEN-CEN-02)
MESSAGE_LEAD = 15  # ALIEN-CEN-01


def board_data(species: str) -> dict[str, Any]:
    data: dict[str, Any] = tables.alien_boards()[species]
    return data


def new_board(species: str) -> dict[str, list[list[int]]]:
    """An empty species board: for each color a list of spaces, each a list of the players' markers on it (bottom of the list = oldest)."""
    return {c["color"]: [[] for _ in c["spaces"]] for c in board_data(species)["columns"]}


# ---------------------------------------------------------------------------------------------------------------------------------
# marking spaces on a discovered board (LIFE-04, ALIEN-DATA-10, ALIEN-DATA-11)
# ---------------------------------------------------------------------------------------------------------------------------------


def _cost_ok(p: PlayerState, cost: list[dict[str, Any]]) -> bool:
    for c in cost:
        have = p.data_pool if c["t"] == "data" else p.exofossils
        if have < c["n"]:
            return False
    return True


def board_moves(s: GameState, p: PlayerState, slot_index: int, colors: tuple[str, ...]) -> list[dict[str, Any]]:
    """Spaces of the matching color that are empty (a top capsule is always available) and whose cost the player can pay."""
    slot = s.species[slot_index]
    out: list[dict[str, Any]] = []
    for col in board_data(slot.species)["columns"]:
        color = col["color"]
        if color not in colors:
            continue
        for k, space in enumerate(col["spaces"]):
            if not space["rewards"]:  # Mascamite sample spaces come with the Mascamite slice
                continue
            if slot.board[color][k] and not space.get("repeat"):
                continue
            if _cost_ok(p, space.get("cost", [])):
                out.append({"type": "place_trace", "slot": slot_index, "space": "board", "color": color, "index": k})
    if slot.species == "mascamites" and "blue" in colors:  # ALIEN-MASC-05: a sample token makes its blue space markable by anyone
        out += [
            {"type": "place_trace", "slot": slot_index, "space": "sample", "color": "blue", "index": j}
            for j, sp in enumerate(slot.extra["sample_spaces"])
            if sp["marker"] is None
        ]
    return out


def mark_board_space(s: GameState, p: PlayerState, slot_index: int, color: str, k: int, events: Events) -> None:
    slot = s.species[slot_index]
    space = next(c for c in board_data(slot.species)["columns"] if c["color"] == color)["spaces"][k]
    for c in space.get("cost", []):  # ALIEN-CEN-05, ALIEN-OUM-02: data from the pool, exofossils
        if c["t"] == "data":
            p.data_pool -= c["n"]
        else:
            p.exofossils -= c["n"]
            s.species[oumuamua_slot(s) or 0].extra["supply"] += c["n"]  # paid tokens go back to the supply
    slot.board[color][k].append(p.index)
    rewards.grant(s, p, space["rewards"], events, slot=slot_index)


# ---------------------------------------------------------------------------------------------------------------------------------
# alien cards (ALIEN-04, ALIEN-05, ALIEN-06)
# ---------------------------------------------------------------------------------------------------------------------------------


def alien_card_moves(s: GameState, d: Decision) -> list[dict[str, Any]]:
    slot = s.species[d.data["slot"]]
    out: list[dict[str, Any]] = []
    if slot.deck:
        out.append({"type": "take_alien", "source": "deck"})
    if slot.face_up is not None:
        out.append({"type": "take_alien", "source": "face_up"})
    return out


def take_alien_card(s: GameState, p: PlayerState, slot_index: int, source: str) -> None:
    slot = s.species[slot_index]
    if source == "deck":
        p.hand.append(slot.deck.pop())
    else:
        assert slot.face_up is not None
        p.hand.append(slot.face_up)
        slot.face_up = slot.deck.pop() if slot.deck else None  # replaced with the top card of the deck


def _deal(s: GameState, p: PlayerState, slot: SpeciesSlot) -> None:
    if slot.deck:
        p.hand.append(slot.deck.pop())


# ---------------------------------------------------------------------------------------------------------------------------------
# discovery (ALIEN-01, ALIEN-06, FAQ-40)
# ---------------------------------------------------------------------------------------------------------------------------------


def resolve_discoveries(s: GameState, events: Events) -> bool:
    """Resolve species whose three discovery spaces are full, after the turn and its milestones. Returns True if one was resolved."""
    found = False
    for i, slot in enumerate(s.species):
        # the three spaces decide, not the flag set when the last was filled: a species whose spaces are full is always revealed (ALIEN-01)
        if not slot.discovered and (slot.complete or all(x is not None for x in slot.discovery_spaces)):
            found = True
            _discover(s, i, events)
    return found


def _discover(s: GameState, index: int, events: Events) -> None:
    slot = s.species[index]
    slot.discovered = True
    events.append({"type": "discovered", "species": slot.species, "slot": index})
    ids = sorted(cid for cid, c in tables.cards().items() if c["species"] == slot.species)
    slot.deck = rng.shuffled(s, ids)  # ALIEN-06
    owners = [int(x[1:]) for x in slot.discovery_spaces if x is not None and x != "n"]
    if slot.species == "exertians":
        _setup_exertians(s, slot, owners, events)
        return
    for pl in owners:  # FAQ-40: only the players who marked a discovery space get a card, one per marker
        if rival.is_rival(s, pl):
            rival.on_discovery_markers(s, 1, events)  # SOLO-10: a card for the rival is a space of progress
        else:
            _deal(s, s.players[pl], slot)
    slot.face_up = slot.deck.pop() if slot.deck else None
    if slot.species == "mascamites":
        _setup_mascamites(s, slot, events)
    elif slot.species == "oumuamua":
        _setup_oumuamua(s, slot, events)
    elif slot.species == "anomalies":
        _setup_anomalies(s, slot, events)
    elif slot.species == "centaurians":
        _setup_centaurians(s, slot, events)


# ---------------------------------------------------------------------------------------------------------------------------------
# Anomalies (ALIEN-ANO-01 to ALIEN-ANO-05)
# ---------------------------------------------------------------------------------------------------------------------------------


def _token_reward(color: str, side: int) -> list[dict[str, Any]]:
    faces: list[list[dict[str, Any]]] = next(t for t in board_data("anomalies")["tokens"] if t["column"] == color)["sides"]
    return faces[side]


def _setup_anomalies(s: GameState, slot: SpeciesSlot, events: Events) -> None:
    """ALIEN-ANO-01: one token in Earth's sector, the other two 3 sectors clockwise and counter-clockwise of Earth."""
    from . import solar  # noqa: PLC0415

    earth_sector = solar.earth(s)[1]
    sectors = [earth_sector, (earth_sector + 3) % 8, (earth_sector - 3) % 8]
    cols = rng.shuffled(s, list(COLORS))  # which anomaly goes where is not ruled: seeded random order (A-004)
    slot.extra["tokens"] = [{"sector": sec, "color": col, "side": rng.below(s, 2)} for sec, col in zip(sectors, cols, strict=True)]
    for t in slot.extra["tokens"]:  # the side that is up is public: the page shows what the token pays (ALIEN-ANO-01)
        t["reward"] = _token_reward(t["color"], t["side"])
    events.append(
        {
            "type": "anomalies_placed",
            "earth_sector": earth_sector,
            "tokens": [dict(t) for t in slot.extra["tokens"]],
        }
    )


def anomaly_reward(s: GameState, slot: SpeciesSlot, color: str) -> int | None:
    """ALIEN-ANO-03, ALIEN-ANO-05: the player with the highest marked space of the column (a later marker on the top space is higher)."""
    column = slot.board[color]
    for markers in column:  # from the top of the board down
        if markers:
            return markers[-1]
    return None


def after_rotation(s: GameState, events: Events) -> None:
    """ALIEN-ANO-02: whenever the solar system rotates, an anomaly in Earth's sector is resolved at once."""
    from . import solar  # noqa: PLC0415

    earth_sector = solar.earth(s)[1]
    for slot in s.species:
        if slot.species != "anomalies" or not slot.discovered:
            continue
        for tok in slot.extra["tokens"]:
            if tok["sector"] != earth_sector:
                continue
            winner = anomaly_reward(s, slot, tok["color"])
            reward = _token_reward(tok["color"], tok["side"])
            events.append(
                {"type": "anomaly", "sector": tok["sector"], "color": tok["color"], "side": tok["side"], "reward": reward, "player": winner}
            )
            if winner is not None:
                rewards.grant(s, s.players[winner], reward, events)


# ---------------------------------------------------------------------------------------------------------------------------------
# Mascamites (ALIEN-MASC-01 to ALIEN-MASC-05)
# ---------------------------------------------------------------------------------------------------------------------------------

SAMPLE_PLANETS = ("jupiter", "saturn")  # ALIEN-MASC-01


def mascamite_slot(s: GameState) -> int | None:
    return next((i for i, sl in enumerate(s.species) if sl.species == "mascamites" and sl.discovered), None)


def sample_faces() -> list[list[dict[str, Any]]]:
    faces: list[list[dict[str, Any]]] = board_data("mascamites")["tokens"][0]["sides"]
    return faces


def new_sample_space(token: int) -> dict[str, Any]:
    """A blue space holding a face-up sample token (ALIEN-MASC-05). The token and its reward are public; `marker` is who marked it."""
    return {"token": token, "marker": None, "reward": sample_faces()[token]}


def _setup_mascamites(s: GameState, slot: SpeciesSlot, events: Events) -> None:
    """ALIEN-MASC-01: 7 face-down samples, 3 to Jupiter, 3 to Saturn, the last one face up on its designated blue space."""
    order = rng.shuffled(s, list(range(len(sample_faces()))))
    slot.extra["samples"] = {"jupiter": order[0:3], "saturn": order[3:6]}
    slot.extra["sample_spaces"] = [new_sample_space(order[6])]
    # the face-up token is public; of the others only how many lie on each planet is (they are face down)
    events.append(
        {
            "type": "samples_placed",
            "planets": {planet: len(tokens) for planet, tokens in slot.extra["samples"].items()},
            "face_up": {"token": order[6], "reward": sample_faces()[order[6]]},
        }
    )


def samples_on(s: GameState, planet: str) -> list[int]:
    """The sample tokens lying on a planet's space (only Jupiter and Saturn have any)."""
    i = mascamite_slot(s)
    if i is None:
        return []
    samples: dict[str, list[int]] = s.species[i].extra["samples"]
    return list(samples.get(planet, []))


def return_exofossils(s: GameState, n: int) -> None:
    i = oumuamua_slot(s)
    if i is not None and n:
        s.species[i].extra["supply"] += n


def collect_sample_options(s: GameState, probe_id: str) -> list[int]:
    """ALIEN-MASC-02: the samples lying on the planet the probe is on (none away from Jupiter and Saturn, or once taken)."""
    from . import solar  # noqa: PLC0415

    i = mascamite_slot(s)
    if i is None:
        return []
    probe = next(pr for pr in s.probes if pr.id == probe_id)
    planet = solar.planet_of(solar.visible(s, probe.ring, probe.sector)[1])
    samples: dict[str, list[int]] = s.species[i].extra["samples"]
    return list(samples.get(planet or "", []))


def collect_sample(s: GameState, p: PlayerState, planet: str, token: int, events: Events) -> None:
    """ALIEN-MASC-02: stack a marker on the chosen sample: a capsule starting on the space the token was taken from."""
    from . import solar  # noqa: PLC0415

    i = mascamite_slot(s)
    assert i is not None
    pos = solar.find_cell(s, f"PLANET:{planet.upper()}")
    assert pos is not None
    s.species[i].extra["samples"][planet].remove(token)
    s.probe_counter += 1
    s.probes.append(Probe(id=f"capsule{s.probe_counter}", player=p.index, ring=pos[0], sector=pos[1], capsule=True, sample=token))
    events.append({"type": "sample_collected", "player": p.index, "planet": planet})


def deliver_sample(s: GameState, p: PlayerState, capsule_id: str, events: Events, times: int = 1) -> None:
    """ALIEN-MASC-04: remove the capsule, gain the token's reward, and put the token face up on the next blue sample space."""
    i = mascamite_slot(s)
    assert i is not None
    cap = next(pr for pr in s.probes if pr.id == capsule_id and pr.capsule)
    assert cap.sample is not None
    s.probes.remove(cap)
    s.species[i].extra["sample_spaces"].append(new_sample_space(cap.sample))
    for _ in range(times):  # #ET.7 resolves the delivered sample twice
        rewards.grant(s, p, sample_faces()[cap.sample], events, slot=i)
    events.append(
        {
            "type": "sample_delivered",
            "player": p.index,
            "token": cap.sample,  # revealed on delivery (ALIEN-MASC-04)
            "reward": sample_faces()[cap.sample],
            "space": len(s.species[i].extra["sample_spaces"]) - 1,
            "times": times,
        }
    )


def mark_sample_space(s: GameState, p: PlayerState, slot_index: int, j: int, events: Events) -> None:
    """ALIEN-MASC-05: any player may mark a blue space holding a sample token and gains that token's reward."""
    sp = s.species[slot_index].extra["sample_spaces"][j]
    sp["marker"] = p.index
    events.append({"type": "sample_space_marked", "player": p.index, "space": j, "reward": sample_faces()[sp["token"]]})
    rewards.grant(s, p, sample_faces()[sp["token"]], events, slot=slot_index)


# ---------------------------------------------------------------------------------------------------------------------------------
# Exertians (ALIEN-EXE-01 to ALIEN-EXE-07)
# ---------------------------------------------------------------------------------------------------------------------------------

EXERT_BASE = 20_000  # entries of GameState.crossed at or above this value are Exertian milestones (below it, from MESSAGE_BASE, messages)
EXERT_LEADS = (20, 40)  # ALIEN-EXE-03
TIER_DANGER = (1, 2, 2, 3, 3)  # ALIEN-EXE-06: danger of the markers on the five spaces of a column, top to bottom

# Exertian cards (owner notes for ET.41 to ET.55, ALIEN-DATA-03): id -> (danger, condition, points when the condition is met)
EXERTIAN_CARDS: dict[str, tuple[int, dict[str, Any], int]] = {
    "ET.41": (6, {"c": "techs", "cat": "probe", "n": 3}, 14),
    "ET.42": (7, {"c": "techs", "cat": "telescope", "n": 3}, 15),
    "ET.43": (3, {"c": "techs", "cat": "computer", "n": 3}, 9),
    "ET.44": (4, {"c": "wins", "color": "red", "n": 2}, 12),
    "ET.45": (4, {"c": "wins", "color": "blue", "n": 2}, 12),
    "ET.46": (4, {"c": "wins", "color": "yellow", "n": 2}, 12),
    "ET.47": (5, {"c": "wins", "color": "black", "n": 2}, 14),
    "ET.48": (3, {"c": "orbiters", "n": 3}, 11),
    "ET.49": (7, {"c": "landers", "n": 4}, 16),
    "ET.50": (2, {"c": "one_planet", "n": 3}, 10),
    "ET.51": (8, {"c": "tucked", "n": 8}, 18),
    "ET.52": (0, {"c": "traces_of", "which": "exertians", "n": 6}, 7),
    "ET.53": (9, {"c": "traces_of", "which": "other", "n": 6}, 20),
    "ET.54": (1, {"c": "same_color", "n": 5}, 8),
    "ET.55": (4, {"c": "quick_missions", "n": 5}, 12),
}


def exertian_slot(s: GameState) -> int | None:
    return next((i for i, sl in enumerate(s.species) if sl.species == "exertians" and sl.discovered), None)


def _setup_exertians(s: GameState, slot: SpeciesSlot, owners: list[int], events: Events) -> None:
    """ALIEN-EXE-01, ALIEN-EXE-03, ALIEN-EXE-05: 3 cards each plus 1 per marker, the rest back in the box, two milestone tiles."""
    for p in s.players:
        if s.rival is None or p.index != s.rival.index:  # the rival never holds Exertian cards (SOLO-ALIEN-03)
            p.exertian_hand += [slot.deck.pop() for _ in range(3)]
    for pl in owners:
        if rival.is_rival(s, pl):
            rival.on_discovery_markers(s, 1, events)
        else:
            s.players[pl].exertian_hand.append(slot.deck.pop())
    if s.rival is None:
        slot.deck = []  # the rest goes back to the box; in the solo game the rival draws from it (FAQ-57)
    slot.face_up = None
    lead = max(p.score for p in s.players)
    slot.extra["milestones"] = [{"at": lead + d, "cost": 0 if i == 0 else 1, "done": []} for i, d in enumerate(EXERT_LEADS)]
    events.append(
        {
            "type": "exertian_milestones",
            "leader_score": lead,
            "milestones": [{"at": m["at"], "cost": m["cost"]} for m in slot.extra["milestones"]],
        }
    )
    for pl in owners:  # an immediate chance to play one card per marker
        if not rival.is_rival(s, pl):
            s.pending.append(Decision(kind="exertian_play", player=pl, data={"cost": 0}))


def exertian_play_moves(s: GameState, d: Decision) -> list[dict[str, Any]]:
    p = s.players[d.player]
    can_pay = p.credits >= d.data["cost"]
    cards = [{"type": "play_exertian", "card": c} for c in p.exertian_hand] if can_pay else []
    return [*cards, {"type": "skip_exertian"}]


def play_exertian(s: GameState, p: PlayerState, cid: str, cost: int) -> None:
    p.credits -= cost  # ALIEN-EXE-04
    p.exertian_hand.remove(cid)
    p.exertian_played.append(cid)  # face down: other players do not see which card it is


def board_danger(s: GameState, p: PlayerState) -> int:
    """ALIEN-EXE-06: 3, 2 or 1 danger per marker on the bottom, middle and top of the Exertian board. Public: the board is open."""
    total = 0
    i = exertian_slot(s)
    if i is not None:
        for column in s.species[i].board.values():
            for k, markers in enumerate(column):
                total += TIER_DANGER[k] * markers.count(p.index)
    return total


def cards_danger(p: PlayerState) -> int:
    """ALIEN-EXE-06: the danger of the played cards, which only their owner may know until the end of the game."""
    return sum(EXERTIAN_CARDS[c][0] for c in p.exertian_played)


def danger(s: GameState, p: PlayerState) -> int:
    """ALIEN-EXE-06: the danger of the played cards plus the danger of the markers on the board."""
    return cards_danger(p) + board_danger(s, p)


def exertian_losses(s: GameState, totals: list[int]) -> list[int]:
    """ALIEN-EXE-07: the player with the most danger (all players tied for it) loses one tenth of their total, rounded down."""
    if exertian_slot(s) is None:
        return [0] * len(totals)
    dangers = [danger(s, p) for p in s.players]
    top = max(dangers)
    return [t // 10 if d == top else 0 for t, d in zip(totals, dangers, strict=True)]


# ---------------------------------------------------------------------------------------------------------------------------------
# 'Oumuamua (ALIEN-OUM-01 to ALIEN-OUM-05)
# ---------------------------------------------------------------------------------------------------------------------------------

EXOFOSSILS = 17
TILE_DATA = 3


def oumuamua_slot(s: GameState) -> int | None:
    return next((i for i, sl in enumerate(s.species) if sl.species == "oumuamua" and sl.discovered), None)


def oumuamua_sector(s: GameState) -> int | None:
    """The sector the 'Oumuamua tile is in now (it rides disc 3), once it is on the board."""
    from . import solar  # noqa: PLC0415

    if oumuamua_slot(s) is None:
        return None
    pos = solar.find_cell(s, solar.OUMUAMUA_CELL)
    return None if pos is None else pos[1]


def _setup_oumuamua(s: GameState, slot: SpeciesSlot, events: Events) -> None:
    from . import solar  # noqa: PLC0415
    from .models import PlanetState  # noqa: PLC0415

    slot.extra = {"tile": {"data": TILE_DATA, "markers": []}, "supply": EXOFOSSILS}
    s.oumuamua_placed = True  # ALIEN-OUM-01: the tile covers its cutout in disc 3
    s.planets["oumuamua"] = PlanetState(first_land_data_taken=[False] * 3, first_land_owners=[None] * 3)
    pos = solar.find_cell(s, solar.OUMUAMUA_CELL)
    assert pos is not None
    for pr in s.probes:  # a probe on that space is set on top of the tile and its player gains 1 publicity
        if (pr.ring, pr.sector) == pos:
            effects.gain_publicity(s, s.players[pr.player])
            events.append({"type": "publicity", "player": pr.player, "reason": "oumuamua"})


def gain_exofossil(s: GameState, p: PlayerState, n: int) -> None:
    i = oumuamua_slot(s)
    assert i is not None
    extra = s.species[i].extra
    got = min(n, extra["supply"])  # the supply holds 17 tokens
    extra["supply"] -= got
    p.exofossils += got


def mark_tile(s: GameState, p: PlayerState, events: Events, data: bool = True) -> None:
    """ALIEN-OUM-03: a signal on the tile takes its leftmost data; the first marker scores 1 point, the third 2 points."""
    i = oumuamua_slot(s)
    assert i is not None
    tile = s.species[i].extra["tile"]
    pos = len(tile["markers"])
    tile["markers"].append(p.index)
    if pos < TILE_DATA:
        tile["data"] -= 1
        if data:
            effects.gain_data(s, p, 1)
        if pos == 0:
            effects.gain_score(s, p, 1)
        if pos == 2:
            effects.gain_score(s, p, 2)
        if s.scan_ctx is not None:  # #ET.21, #ET.22: what a scan does with its signals on the tile
            s.scan_ctx["tile"] = s.scan_ctx.get("tile", 0) + 1
            if s.scan_ctx.get("vp_tile"):
                effects.gain_score(s, p, s.scan_ctx["vp_tile"])
        if tile["data"] == 0 and -1 not in s.completed:
            s.completed.append(-1)  # completed like a sector: resolved after the main action
    events.append({"type": "signal_tile", "player": p.index})


def resolve_tile(s: GameState, events: Events) -> None:
    """ALIEN-OUM-04: each player who marked the tile gains 1 exofossil; no winner; the tile is refilled with no markers left."""
    i = oumuamua_slot(s)
    assert i is not None
    tile = s.species[i].extra["tile"]
    for pl in sorted(set(tile["markers"])):
        gain_exofossil(s, s.players[pl], 1)
    tile["data"], tile["markers"] = TILE_DATA, []


# ---------------------------------------------------------------------------------------------------------------------------------
# Centaurians (ALIEN-CEN-01, ALIEN-CEN-03 to ALIEN-CEN-05)
# ---------------------------------------------------------------------------------------------------------------------------------


def _setup_centaurians(s: GameState, slot: SpeciesSlot, events: Events) -> None:
    slot.extra["covered"] = [None, None, None, None]  # which player's message tile covers each reward hex
    for p in s.players:  # ALIEN-CEN-01: a message milestone 15 points ahead of the player's marker
        add_message(s, p)
    events.append({"type": "messages_placed", "targets": [{"player": p.index, "target": p.messages[-1]} for p in s.players]})
    if s.rival is not None:
        s.rival.messages_in_reserve = rival.RIVAL_MESSAGE_RESERVE  # SOLO-ALIEN-02: the rival keeps the leftover tiles


def add_message(s: GameState, p: PlayerState) -> None:
    p.messages.append(p.score + MESSAGE_LEAD)


def message_slot(s: GameState) -> int | None:
    return next((i for i, sl in enumerate(s.species) if sl.species == "centaurians" and sl.discovered), None)


def message_moves(s: GameState) -> list[dict[str, Any]]:
    i = message_slot(s)
    assert i is not None
    covered = s.species[i].extra["covered"]
    rewards_of = board_data("centaurians")["message_rewards"]
    return [{"type": "choose_message", "hex": k, "reward": rewards_of[k]} for k, c in enumerate(covered) if c is None]


def reach_message(s: GameState, p: PlayerState, hex_index: int, events: Events) -> None:
    """ALIEN-CEN-04: cover the chosen reward with the message tile and gain it."""
    i = message_slot(s)
    assert i is not None
    s.species[i].extra["covered"][hex_index] = p.index
    reward = board_data("centaurians")["message_rewards"][hex_index]
    events.append({"type": "message_reward", "player": p.index, "hex": hex_index, "reward": reward})
    rewards.grant(s, p, reward, events, slot=i)


def check_messages(s: GameState, p: PlayerState, before: int) -> None:
    """Called when a player's score rises: a message target reached or passed is resolved at the end of the turn (MILE-01)."""
    for target in sorted(p.messages):
        if before < target <= p.score:
            s.crossed.append((p.index, MESSAGE_BASE + target))
    for mc in p.message_cards:  # ALIEN-CEN-03: the oldest message first
        if before < mc.target <= p.score:
            s.crossed.append((p.index, CARD_MESSAGE_BASE + mc.target))


def check_exertian_milestones(s: GameState, p: PlayerState, before: int) -> None:
    """ALIEN-EXE-03: each player crosses each Exertian milestone once, and may then play a card."""
    i = exertian_slot(s)
    if i is None or rival.is_rival(s, p.index):  # the rival ignores the Exertian milestones (SOLO-ALIEN-03)
        return
    for k, m in enumerate(s.species[i].extra["milestones"]):
        if p.index not in m["done"] and before < m["at"] <= p.score:
            m["done"].append(p.index)
            s.crossed.append((p.index, EXERT_BASE + k))
