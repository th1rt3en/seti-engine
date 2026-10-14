"""The rules engine entry points: `start`, `legal_moves`, `apply`.

`apply` is pure: it copies the state, applies one action and returns the new state, the events and the next legal moves. The engine is
the only place rules live (CLAUDE.md rule 5); every rule cites its spec ID.

Implemented so far: setup, the turn and round structure, passing, income, milestones (gold choice and neutral markers), the Launch action,
probe movement, the free actions (movement for energy, buying a card, resource exchange for credits and energy, discarding a card for
its corner, placing data) and solar system rotation. See services/engine/PROGRESS.md for what is next.
"""

from __future__ import annotations

import heapq
from typing import Any

from pydantic import BaseModel

from . import alien_steps, cards, effects, objectives, orgs, rewards, rival, sandbox, scoring, solar, species, tables, techs
from .models import Decision, GameState, Options, PlayerState, Probe
from .setup import new_game

Action = dict[str, Any]
Events = list[dict[str, Any]]
COMPUTER_PUBLICITY_POS = 1  # BOARD-71: top-row space 2 gives 1 publicity
COMPUTER_INCOME_POS = 3  # BOARD-71: top-row space 4 lets the player tuck a card
COMPUTER_TECH_POS = (0, 2, 4, 5)  # BOARD-72
GOLD_MILESTONES = (25, 50, 70)
NEUTRAL_MILESTONES = (20, 30)


class IllegalAction(Exception):
    pass


class StepResult(BaseModel):
    state: GameState
    events: list[dict[str, Any]]
    legal: list[Action]


def start(options: Options) -> StepResult:
    state = new_game(options)
    return StepResult(state=state, events=[{"type": "new_game"}], legal=legal_moves(state))


# ---------------------------------------------------------------------------------------------------------------------------------
# legal moves
# ---------------------------------------------------------------------------------------------------------------------------------


probe_limit = effects.probe_limit  # LAUNCH-02, LAUNCH-03


def probes_in_space(state: GameState, p: PlayerState) -> list[Probe]:
    return [pr for pr in state.probes if pr.player == p.index]


def leave_cost(state: GameState, p: PlayerState, ring: int, sector: int) -> int:
    """Cost to leave a space: 1, plus 1 on asteroids unless the player has the asteroid tech (MOVE-02, TECH-PT03)."""
    cell = solar.visible(state, ring, sector)[1]
    ignore = cards.fx_active(state, "ignore_asteroid")  # FAQ-C026
    extra = 1 if cell == "ASTEROID" and not effects.tech_active(p, "probe-link") and not ignore else 0
    return 1 + extra


def move_cost(state: GameState, p: PlayerState, probe: Probe) -> int:
    """Cost to move the probe one space (MOVE-01, MOVE-02): the cost to leave the space it is in."""
    return leave_cost(state, p, probe.ring, probe.sector)


def move_reach(state: GameState, p: PlayerState) -> list[tuple[str, list[tuple[tuple[int, int], int, list[tuple[int, int]]]]]]:
    """Where each of the player's probes can go with the movement they have plus all their energy (FREE-01: 1 energy is 1 movement).

    For every probe: the spaces it can reach, each with the least movement it takes and one cheapest path (the spaces entered, in order).
    Cheapest paths come from Dijkstra over the adjacency of BOARD-16, so they follow exactly the costs `apply` charges for the single steps.
    """
    budget = p.movement + p.energy
    out: list[tuple[str, list[tuple[tuple[int, int], int, list[tuple[int, int]]]]]] = []
    for pr in probes_in_space(state, p):
        start = (pr.ring, pr.sector)
        best: dict[tuple[int, int], int] = {start: 0}
        came: dict[tuple[int, int], tuple[int, int]] = {}
        heap: list[tuple[int, tuple[int, int]]] = [(0, start)]
        while heap:
            cost, cell = heapq.heappop(heap)
            if cost > best[cell]:
                continue
            step = leave_cost(state, p, *cell)
            for nb in solar.adjacent(*cell):
                nxt = cost + step
                if nxt <= budget and nxt < best.get(nb, 1 << 30):
                    best[nb] = nxt
                    came[nb] = cell
                    heapq.heappush(heap, (nxt, nb))
        cells = []
        for cell, cost in sorted(best.items()):
            if cell == start:
                continue
            path = [cell]
            while came[path[-1]] != start:
                path.append(came[path[-1]])
            cells.append((cell, cost, path[::-1]))
        out.append((pr.id, cells))
    return out


def legal_moves(state: GameState) -> list[Action]:
    if state.phase == "finished":
        return []
    if state.pending:
        d = state.pending[0]
        answers = _decision_moves(state, d)
        if _can_interrupt(state, d):  # FREE-00: a free action may interrupt the main action
            answers += [m for m in _free_moves(state, state.players[state.current_player]) if m not in answers]
        if _can_undo(state) and d.player == state.current_player:
            answers.append({"type": "undo"})  # UNDO-01
        return answers
    if state.phase != "play":
        return []
    p = state.players[state.current_player]
    moves: list[Action] = _free_moves(state, p)
    if _can_undo(state):
        moves.append({"type": "undo"})  # UNDO-01
    if not state.main_done:
        moves += _main_moves(state, p)
    else:
        moves.append({"type": "end_turn"})
    if state.options.sandbox:
        moves.append(sandbox.marker(state))  # D33
    return moves


def _can_interrupt(state: GameState, d: Decision) -> bool:
    """FREE-00: a decision of the main action can be interrupted by a free action; one of a free action, of resolving sectors, milestones or
    passing cannot."""
    return (
        state.phase == "play"
        and state.stage is None
        and not state.free_active
        and d.player == state.current_player
        and not rival.is_rival(state, state.current_player)
    )


def _can_undo(state: GameState) -> bool:
    return state.phase == "play" and state.undo is not None and len(state.undo_log) > 0 and state.stage in (None, "sectors")


def _decision_moves(state: GameState, d: Decision) -> list[Action]:
    p = state.players[d.player]
    if d.kind == "data_overflow":  # RES-01 (owner ruling 2026-10-14): place pool data first, or take the data and lose the extra
        place: list[Action] = [{"type": "place_data"}] if p.data_pool >= 1 and not all(p.computer) else []
        return [*place, *techs.lower_moves(p), {"type": "data_done"}]
    if d.kind == "sector_order":  # TURN-05 (owner ruling 2026-10-14): the player chooses which completed sector is resolved next
        return [{"type": "resolve_sector", "sector": i} for i in d.data["sectors"] if i in state.completed]
    if d.kind in ("choose_org", "choose_quick"):
        return orgs.choose_moves(state, d)  # EXP-ORG-04
    if d.kind == "org_mark":
        return orgs.mark_moves(state, d)  # EXP-ORG-11
    if d.kind == "setup_tuck":
        return [{"type": "tuck", "card": c} for c in dict.fromkeys(p.hand)]
    if d.kind == "income_tuck":
        return [{"type": "tuck", "card": c} for c in dict.fromkeys(p.hand)] + [{"type": "skip_tuck"}]
    if d.kind == "discard_to_four":
        return [{"type": "discard", "card": c} for c in dict.fromkeys(p.hand)]
    if d.kind == "take_round_card":
        return [{"type": "take_round_card", "card": c} for c in state.end_of_round_stacks[state.round - 1]]
    moves = cards.decision_moves(state, d)
    if moves is not None:
        return moves
    if d.kind == "orbit_land_free":
        return _orbit_land_free_moves(state, p, d)
    if d.kind == "exertian_play":
        return species.exertian_play_moves(state, d)
    if d.kind == "objective_task":
        return [{"type": "mark_objective", "objective": o, "task": i} for o, i in d.data["options"]]
    if d.kind == "oumuamua_signal":
        return [{"type": "signal_where", "where": "sector"}, {"type": "signal_where", "where": "tile"}]
    if d.kind == "take_alien_card":
        return species.alien_card_moves(state, d)
    if d.kind == "message_reward":
        return species.message_moves(state)
    if d.kind == "research_tech":
        return cards.research_moves(d)
    if d.kind == "land_free":
        return cards.land_free_moves(state, p, d.data)
    if d.kind == "take_card":
        return [{"type": "take_card", "source": "deck"}] + [{"type": "take_card", "source": f"row:{i}"} for i in range(len(state.card_row))]
    if d.kind == "scan_step":
        return techs.scan_moves(state, p)
    if d.kind == "computer_slot":
        return [{"type": "place_computer_tech", "slot": k} for k in d.data["slots"]]
    if d.kind == "signal":
        if d.data["color"] == "any":
            return [{"type": "mark_signal", "sector": i} for i in range(len(state.sectors))]
        return [{"type": "mark_signal", "sector": i} for i in rewards.sectors_of_color(state, d.data["color"])]
    if d.kind == "trace":
        return rewards.trace_moves(state, d)
    if d.kind == "land_data_slot":
        return [{"type": "choose_land_slot", "slot": k} for k in d.data["slots"]]
    if d.kind == "gold_choice":
        return [
            {"type": "choose_gold", "tile": g.tile} for g in state.gold_tiles if d.player not in g.markers and d.player not in g.low_markers
        ]
    raise ValueError(d.kind)


def _exchange_moves(state: GameState, p: PlayerState) -> list[Action]:
    """RES-06: 2 cards, 2 credits or 2 energy of one kind for 1 card, 1 credit or 1 energy; a card is from the card row or the deck top."""
    sources = ["deck", *(f"row:{i}" for i in range(len(state.card_row)))]
    out: list[Action] = []
    for give in ("credit", "energy"):
        if (p.credits if give == "credit" else p.energy) >= 2:
            out += [{"type": "exchange", "give": give, "get": g} for g in ("credit", "energy") if g != give]
            out += [{"type": "exchange", "give": give, "get": "card", "source": src} for src in sources]
    hand = sorted(p.hand)
    pairs = sorted({(a, b) for i, a in enumerate(hand) for b in hand[i + 1 :]})  # two cards of the hand (alien cards count)
    for a, b in pairs:
        out += [{"type": "exchange", "give": "card", "cards": [a, b], "get": g} for g in ("credit", "energy")]
        out += [{"type": "exchange", "give": "card", "cards": [a, b], "get": "card", "source": src} for src in sources]
    return out


def _free_moves(state: GameState, p: PlayerState) -> list[Action]:
    out: list[Action] = []
    if p.energy >= 1:
        out.append({"type": "move_energy"})  # FREE-01
    if p.movement > 0:
        for pr in probes_in_space(state, p):
            cost = move_cost(state, p, pr)
            if cost <= p.movement:
                for ring, sector in solar.adjacent(pr.ring, pr.sector):
                    out.append({"type": "move_probe", "probe": pr.id, "to": [ring, sector]})
    if p.publicity >= 3:  # FREE-06
        out.append({"type": "buy_card", "source": "deck"})
        out += [{"type": "buy_card", "source": f"row:{i}"} for i in range(len(state.card_row))]
    out += _exchange_moves(state, p)  # RES-06
    for cid in dict.fromkeys(p.hand):  # FREE-02
        if tables.cards()[cid]["free"]:
            out.append({"type": "discard_free", "card": cid})
    if p.data_pool >= 1 and not all(p.computer):
        out.append({"type": "place_data"})  # FREE-03
    out += techs.lower_moves(p)  # TECH-21
    out += cards.mission_moves(state, p)  # FREE-07
    out += orgs.free_moves(state, p)  # EXP-ORG-10
    return out


def _main_moves(state: GameState, p: PlayerState) -> list[Action]:
    out: list[Action] = [{"type": "pass"}, *cards.play_moves(state, p)]  # PLAY-01
    if p.credits >= 2 and sum(1 for pr in probes_in_space(state, p) if not pr.capsule) < probe_limit(p):
        out.append({"type": "launch"})  # LAUNCH-01, LAUNCH-02
    for pr in probes_in_space(state, p):
        planet = planet_at(state, pr)
        if planet is None or pr.capsule:  # a sample capsule cannot orbit or land (ALIEN-MASC-03)
            continue
        if p.credits >= 1 and p.energy >= 1:
            out.append({"type": "orbit", "probe": pr.id})  # ORBIT-01
        if p.energy >= land_cost(state, p, planet):
            out.append({"type": "land", "probe": pr.id})  # LAND-01
            if effects.tech_active(p, "probe-cross"):  # LAND-05, TECH-PT04
                for moon in tables.planet_info(planet)["moons"]:
                    if moon not in state.planets[planet].moon_landers:
                        out.append({"type": "land", "probe": pr.id, "moon": moon})
    out += orgs.main_moves(
        state, p, sum(1 for pr in probes_in_space(state, p) if not pr.capsule) < probe_limit(p), techs.research_moves(state, p)
    )  # EXP-ORG-12, EXP-ORG-13
    out += _pluto_moves(state, p)  # PROMO-02
    if p.credits >= 1 and p.energy >= 2:
        out.append({"type": "scan"})  # SCAN-01
    if p.publicity >= orgs.research_cost(p, techs.RESEARCH_COST):
        out += techs.research_moves(state, p)  # TECHACT-01
    if techs.can_analyze(p):
        out.append({"type": "analyze"})  # ANALYZE-01
    return out


OUTERMOST_RING = 4  # the ring of Uranus and Neptune


def _pluto_moves(state: GameState, p: PlayerState) -> list[Action]:
    """PROMO-02, FAQ-C300: the owner of SE EN 01 may orbit or land at Pluto with a probe on any space of the outermost ring: one orbiter
    and one lander at most, at the normal costs."""
    if state.pluto_owner != p.index or "pluto" not in state.planets:
        return []
    st = state.planets["pluto"]
    out: list[Action] = []
    for pr in probes_in_space(state, p):
        if pr.capsule or pr.ring != OUTERMOST_RING:
            continue
        if not st.orbiters and p.credits >= 1 and p.energy >= 1:
            out.append({"type": "orbit", "probe": pr.id, "at": "pluto"})
        if not st.landers and p.energy >= land_cost(state, p, "pluto"):
            out.append({"type": "land", "probe": pr.id, "at": "pluto"})
    return out


def planet_at(state: GameState, probe: Probe) -> str | None:
    """The planet (other than Earth) the probe stands on, if any (ORBIT-01, LAND-01)."""
    name = solar.planet_of(solar.visible(state, probe.ring, probe.sector)[1])
    return name if name in state.planets else None


def land_cost(state: GameState, p: PlayerState, planet: str) -> int:
    """LAND-01, LAND-02: 3 energy, 2 if the planet has an orbiter, 1 less with probe tech PT#02 (glyph branch)."""
    cost = 2 if state.planets[planet].orbiters else 3
    return cost - (1 if effects.tech_active(p, "probe-branch") else 0)


# ---------------------------------------------------------------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------------------------------------------------------------


FREE_TYPES = frozenset(
    {
        "move_energy",
        "move_probe",
        "buy_card",
        "exchange",
        "discard_free",
        "place_data",
        "place_lower",
        "complete_mission",
        "deliver_sample",
        "org_free",
    }
)  # the free actions (FREE-01 to FREE-07, TECH-21)
# moves that never show anything hidden, so there is no need to try them out to know whether they can be taken back
NEVER_REVEAL = frozenset({"move_energy", "move_probe", "place_data", "place_lower", "launch", "undo", "sandbox"})


def apply(state: GameState, action: Action) -> StepResult:
    legal = legal_moves(state)
    if sandbox.is_sandbox_action(action):  # D33: too many to list, so they are checked on their own
        why = sandbox.check(state, action)
        if why is not None:
            raise IllegalAction(f"{action} is not allowed: {why}")
    elif action not in legal:
        raise IllegalAction(f"{action} is not legal; legal moves: {legal}")
    if action == {"type": "undo"}:  # UNDO-01: back to the state before the last move; the moves before it are played again
        back = _undo(state)
        return StepResult(state=back, events=[{"type": "undo", "player": state.current_player}], legal=legal_moves(back))
    s, events = _step(state, action)
    events += _deltas(state, s)
    # UNDO-01 (owner, 2026-10-14): every move can be taken back unless it shows something hidden (a card drawn from the deck, a card of the
    # round pile, a species revealed, the next tech tile) or the turn moves on
    if (
        state.phase != "play"
        or _reveals(state, s)
        or (s.round, s.turn, s.current_player, s.phase) != (state.round, state.turn, state.current_player, state.phase)
        or state.stage not in (None, "sectors")
        or s.stage not in (None, "sectors")
    ):
        s.undo, s.undo_log = None, []
    elif state.undo is None:
        s.undo, s.undo_log = _snapshot(state), [action]
    else:
        s.undo, s.undo_log = state.undo, [*state.undo_log, action]
    return StepResult(state=s, events=events, legal=legal_moves(s))


def _step(state: GameState, action: Action) -> tuple[GameState, list[dict[str, Any]]]:
    """Play one legal action on a copy of the state and run the automatic steps after it. No undo bookkeeping."""
    s = state.model_copy(deep=True)
    events: list[dict[str, Any]] = []
    if s.pending and action not in _decision_moves(s, s.pending[0]):
        # FREE-00: a free action in the middle of the main action; the decisions of the main action wait until the free action is done
        s.stashed, s.pending = s.pending, []
        s.free_active = True
        _do_action(s, action, events)
    elif s.pending:
        _resolve_decision(s, action, events)
    elif sandbox.is_sandbox_action(action):
        sandbox.apply_action(s, action, events)
    else:
        _do_action(s, action, events)
        if action["type"] in FREE_TYPES:
            s.free_active = True
    _advance(s, events)
    objectives.check_thresholds(s)  # SOLO-OBJ-04: reaching a level marks the task at once
    return s, events


def _undo(state: GameState) -> GameState:
    assert state.undo is not None
    base = GameState.model_validate(state.undo)
    log = state.undo_log[:-1]
    s = base
    for a in log:
        s, _ = _step(s, a)
    s.undo, s.undo_log = (state.undo, log) if log else (None, [])
    return s


def _hidden(s: GameState) -> tuple[Any, ...]:
    """Everything a player may not see (CLAUDE.md rule 6, projection.py): if a move changes it, the move showed something."""
    return (
        s.deck,
        s.end_of_round_stacks,
        s.aside,
        [(sl.discovered, sl.deck, sl.face_up) for sl in s.species],
        [len(st.tiles) for st in s.tech_stacks],
        s.rival.deck if s.rival else None,
        s.objectives.stack if s.objectives else None,
        [(sl.extra.get("samples"), sl.extra.get("sample_spaces")) for sl in s.species if sl.species == "mascamites"],
        any(d.kind in ("mascamite_sample", "take_round_card") for d in s.pending),  # the player looks at the samples, at the round pile
    )


def _reveals(before: GameState, after: GameState) -> bool:
    return _hidden(before) != _hidden(after)


def reveals(state: GameState, action: Action) -> bool:
    """Would this move show something hidden, so that it could not be taken back? The page warns before such a move (UNDO-01)."""
    if action["type"] in NEVER_REVEAL:
        return False
    try:
        after, _ = _step(state, action)
    except Exception:  # a move that cannot be tried out here is not announced as one that shows something
        return False
    return _reveals(state, after)


def _snapshot(state: GameState) -> dict[str, Any]:
    return state.model_copy(update={"undo": None}).model_dump(mode="json")


def _deltas(before: GameState, after: GameState) -> list[dict[str, Any]]:
    """What each player gained or lost in this step, net: a `delta` event for each player whose points or resources changed (the log)."""
    out: list[dict[str, Any]] = []
    for old, new in zip(before.players, after.players, strict=True):
        changes = {
            "vp": new.score - old.score,
            "credit": new.credits - old.credits,
            "energy": new.energy - old.energy,
            "publicity": new.publicity - old.publicity,
            "data": new.data_pool - old.data_pool,
            "card": len(new.hand) - len(old.hand),
        }
        changes = {k: v for k, v in changes.items() if v != 0}
        if changes:
            out.append({"type": "delta", "player": new.index, "changes": changes})
    return out


def _do_action(s: GameState, a: Action, events: list[dict[str, Any]]) -> None:
    p = s.players[s.current_player]
    t = a["type"]
    if t == "launch":  # LAUNCH-01: pay 2 credits, place a probe on Earth; a main action
        effects.pay(p, credits=2)
        effects.launch_probe(s, p, events)
        s.main_done = True
    elif t == "play_card":
        s.main_done = True
        cards.play(s, p, a["card"], events)
    elif t == "org_main":
        _org_main(s, p, a, events)
    elif t == "complete_mission":
        cards.complete_quick(s, p, a["card"], events)
    elif t == "deliver_sample":
        cards.deliver(s, p, a["card"], a["capsule"], events)
    elif t == "orbit":
        _orbit(s, p, a, events)
    elif t == "land":
        _land(s, p, a, events)
    elif t == "scan":  # SCAN-01, SCAN-02: pay, a signal in Earth's sector, then discard a row card for a second signal (SCAN-03)
        effects.pay(p, credits=1, energy=2)
        s.main_done = True
        techs.start_scan(s, p)
        events.append({"type": "scan", "player": p.index})
        cards.fire(s, p, [{"e": "scan"}], events)  # FAQ-C101
    elif t == "research":  # TECHACT-01, TECHACT-02: pay 6 publicity, rotate, then take the tech
        effects.pay(p, publicity=orgs.research_cost(p, techs.RESEARCH_COST))  # EXP-ORG-13: Fenwick needs 5
        s.main_done = True
        _rotate(s, events)
        techs.take_tech(s, p, a["stack"], events)
        cards.fire(s, p, [{"e": "tech", "cat": s.tech_stacks[a["stack"]].category}], events)
    elif t == "analyze":
        techs.analyze(s, p, events)
        s.main_done = True
    elif t == "place_lower":
        techs.place_lower(s, p, a["slot"], events)
    elif t == "pass":
        p.passed = True
        s.main_done = True
        s.stage = "pass"
        s.pass_discard_checked = False
        s.pass_rotated = False
        s.pass_card_asked = False
        events.append({"type": "pass", "player": p.index})
    elif t == "end_turn":
        s.stage = "turn_end"
    elif t == "move_energy":
        p.energy -= 1
        p.movement += 1
    elif t == "move_probe":
        probe = next(pr for pr in s.probes if pr.id == a["probe"])
        p.movement -= move_cost(s, p, probe)
        old_ring = probe.ring
        probe.ring, probe.sector = a["to"]
        cell = solar.visible(s, probe.ring, probe.sector)[1]
        if cell.startswith("PLANET:") and cards.fx_active(s, "slingshot"):  # FAQ-C019
            s.pending.append(Decision(kind="slingshot", player=p.index))
        elif cards.fx_active(s, "no_pub_move"):  # #ET.12: no publicity for moving probes this turn
            pass
        elif solar.has_publicity_icon(cell) or (cell == "ASTEROID" and effects.tech_active(p, "probe-link")):  # MOVE-05, TECH-PT03
            effects.gain_publicity(s, p)
            events.append({"type": "publicity", "player": p.index, "reason": "visit"})
        events.append({"type": "move", "player": p.index, "probe": probe.id, "to": a["to"]})
        cards.on_move(s, p, old_ring, probe.ring, cell, events)
    elif t == "buy_card":
        effects.pay(p, publicity=3)
        effects.take_from_row_or_deck(s, p, a["source"])
    elif t == "exchange":  # RES-06
        if a["give"] == "card":
            for cid in a["cards"]:
                p.hand.remove(cid)
                s.discard.append(cid)
        elif a["give"] == "credit":
            p.credits -= 2
        else:
            p.energy -= 2
        if a["get"] == "card":
            effects.take_from_row_or_deck(s, p, a["source"])
        elif a["get"] == "credit":
            p.credits += 1
        else:
            p.energy += 1
    elif t == "discard_free":
        p.hand.remove(a["card"])
        s.discard.append(a["card"])
        cards.gain_corner(s, p, a["card"])
        corners = {k for k, _ in tables.cards()[a["card"]]["free"] if k in ("publicity", "data", "move")}
        cards.fire(s, p, [{"e": "discard_free", "corner": k} for k in corners], events)  # FAQ-C138
    elif t == "place_data":
        _place_data(s, p, events)
    elif t == "org_free":
        orgs.free_action(s, p, a, events)  # EXP-ORG-10


def _org_main(s: GameState, p: PlayerState, a: Action, events: list[dict[str, Any]]) -> None:
    """EXP-ORG-12, EXP-ORG-13: Xenolab's discounted actions (the tile flips inactive) and Futurespan's prepared card played for free."""
    s.main_done = True
    if a["org"] == "futurespan_institute":
        cid = p.org_data.pop("fs_card")
        p.org_data.pop("fs_token")
        p.hand.append(cid)  # the prepared card is not in the hand, so it goes back for the play
        cards.play(s, p, cid, events, free=True)
        return
    p.org_data["tiles"][a["tile"]] = False
    if a["tile"] == "launch":
        effects.pay(p, credits=1)
        effects.launch_probe(s, p, events)
    elif a["tile"] == "scan":
        effects.pay(p, energy=2)
        techs.start_scan(s, p)
        events.append({"type": "scan", "player": p.index})
        cards.fire(s, p, [{"e": "scan"}], events)
    else:
        effects.pay(p, publicity=4)
        _rotate(s, events)
        techs.take_tech(s, p, a["stack"], events)
        cards.fire(s, p, [{"e": "tech", "cat": s.tech_stacks[a["stack"]].category}], events)


def _orbit_land_free_moves(s: GameState, p: PlayerState, d: Decision) -> list[Action]:
    """#ET.3: an orbit or land action without paying its cost."""
    out: list[Action] = []
    for pr in probes_in_space(s, p):
        if not pr.capsule and planet_at(s, pr) is not None:
            out.append({"type": "orbit_free", "probe": pr.id})
    return out + cards.land_free_moves(s, p, d.data)


def _orbit(s: GameState, p: PlayerState, a: Action, events: Events, free: bool = False, opts: dict[str, Any] | None = None) -> None:
    """ORBIT-01 to ORBIT-05."""
    probe = next(pr for pr in s.probes if pr.id == a["probe"])
    planet = "pluto" if a.get("at") == "pluto" else planet_at(s, probe)
    assert planet is not None
    data = tables.planet_info(planet)
    if not free:
        effects.pay(p, credits=1, energy=1)
        s.main_done = True
    s.probes.remove(probe)  # ORBIT-02: no longer counts against the probe limit
    st = s.planets[planet]
    first = st.first_orbiter is None
    st.orbiters.append(p.index)
    if first:
        st.first_orbiter = p.index
    p.orbiters[planet] = p.orbiters.get(planet, 0) + 1
    events.append({"type": "orbit", "player": p.index, "planet": planet})
    if first:
        rewards.grant(s, p, data["first_orbit"], events, slot=species.oumuamua_slot(s))  # ORBIT-04
    rewards.grant(s, p, data["orbit"], events, planet, slot=species.oumuamua_slot(s))  # ORBIT-03, ORBIT-05
    cards.fire(s, p, [{"e": "orbit", "planet": planet}, {"e": "orbit_or_land"}], events)  # FAQ-C117
    if (opts or {}).get("collect"):  # Mascamite cards: then look at the samples on the planet and pick one up
        s.queue.insert(0, {"t": "collect_sample", "planet": planet})


def _land(s: GameState, p: PlayerState, a: Action, events: Events, free: bool = False, opts: dict[str, Any] | None = None) -> None:
    """LAND-01 to LAND-06. A moon landing gives the moon's rewards only (ambiguity A-016). `free` is a landing from a card effect."""
    opts = opts or {}
    probe = next(pr for pr in s.probes if pr.id == a["probe"])
    planet = "pluto" if a.get("at") == "pluto" else planet_at(s, probe)
    assert planet is not None
    data = tables.planet_info(planet)
    if not free:
        effects.pay(p, energy=land_cost(s, p, planet))
        s.main_done = True
    s.probes.remove(probe)
    st = s.planets[planet]
    is_moon = "moon" in a
    if opts.get("bonus_vp") and (planet in opts.get("bonus_planets", []) or (is_moon and opts.get("bonus_moon"))):
        effects.gain_score(s, p, opts["bonus_vp"])  # #13 Perseverance Rover
    if is_moon:
        st.moon_landers.setdefault(a["moon"], p.index)
        p.landers[a["moon"]] = p.landers.get(a["moon"], 0) + 1
        events.append({"type": "land", "player": p.index, "planet": planet, "moon": a["moon"]})
        rewards.grant(s, p, data["moons"][a["moon"]], events, planet)
        cards.fire(s, p, [{"e": "land", "planet": planet}, {"e": "orbit_or_land"}], events)
        if opts.get("collect"):
            s.queue.insert(0, {"t": "collect_sample", "planet": planet})
        return
    st.landers.append(p.index)
    p.landers[planet] = p.landers.get(planet, 0) + 1
    events.append({"type": "land", "player": p.index, "planet": planet})
    if opts.get("occupied"):  # FAQ-C016: the covered reward is gained again
        open_slots = list(range(len(st.first_land_data_taken)))
    else:
        open_slots = [k for k, taken in enumerate(st.first_land_data_taken) if not taken]
    if len(open_slots) == 1:  # LAND-04
        _take_land_data(s, p, planet, open_slots[0])
    elif open_slots:  # Mars: the first two landers each choose a space
        s.pending.append(Decision(kind="land_data_slot", player=p.index, data={"planet": planet, "slots": open_slots}))
    rewards.grant(s, p, data["land"], events, planet, slot=species.oumuamua_slot(s))  # LAND-03
    cards.fire(s, p, [{"e": "land", "planet": planet}, {"e": "orbit_or_land"}], events)  # FAQ-C117
    if opts.get("collect"):  # Mascamite cards: then look at the samples on the planet and pick one up
        s.queue.insert(0, {"t": "collect_sample", "planet": planet})


def _take_land_data(s: GameState, p: PlayerState, planet: str, slot: int) -> None:
    s.planets[planet].first_land_data_taken[slot] = True
    s.planets[planet].first_land_owners[slot] = p.index
    effects.gain_data(s, p, tables.planet_info(planet)["first_land_data"][slot])


def _place_data(s: GameState, p: PlayerState, events: list[dict[str, Any]]) -> None:
    """FREE-03/FREE-04: move one data from the pool to the leftmost empty top-row space and resolve that space at once."""
    p.data_pool -= 1
    pos = p.computer.index(False)
    p.computer[pos] = True
    if pos == COMPUTER_PUBLICITY_POS:
        effects.gain_publicity(s, p)
    elif pos in p.computer_techs:
        effects.gain_score(s, p, 2)  # TECH-20: the upper space of a computer tech gives 2 points
    elif pos == COMPUTER_INCOME_POS:
        s.pending.append(Decision(kind="income_tuck", player=p.index))  # INCOME-02; the player may decline (FAQ-01)
    events.append({"type": "place_data", "player": p.index, "position": pos})


def _resolve_data_overflow(s: GameState, p: PlayerState, d: Decision, a: Action, events: list[dict[str, Any]]) -> None:
    """RES-01: each placement makes room; when the gain fits, or the player is done, or nothing more can be placed, the data is taken."""
    t = a["type"]
    if t == "place_data":
        _place_data(s, p, events)
    elif t == "place_lower":
        techs.place_lower(s, p, a["slot"], events)
    n = d.data["n"]
    if t != "data_done" and p.data_pool + n > effects.DATA_POOL_CAP and effects.can_place_data(p):
        s.pending.append(Decision(kind="data_overflow", player=p.index, data={"n": n}))
        return
    p.data_pool = min(effects.DATA_POOL_CAP, p.data_pool + n)


def _resolve_decision(s: GameState, a: Action, events: list[dict[str, Any]]) -> None:
    d = s.pending.pop(0)
    p = s.players[d.player]
    t = a["type"]
    if d.kind == "data_overflow":
        _resolve_data_overflow(s, p, d, a, events)
        return
    if d.kind == "sector_order":
        s.completed.remove(a["sector"])
        rewards.resolve_sector(s, a["sector"], events)
        return
    if d.kind in ("choose_org", "choose_quick"):
        orgs.resolve_choice(s, p, d, a, events)
    elif d.kind == "org_mark":
        orgs.resolve_mark(s, p, a)
    elif t == "tuck":
        effects.tuck_card(s, p, a["card"])
        events.append({"type": "tuck", "player": p.index, "card": a["card"]})
    elif t == "skip_tuck":
        pass
    elif t == "discard":
        p.hand.remove(a["card"])
        s.discard.append(a["card"])
        if len(p.hand) > 4:
            s.pending.insert(0, Decision(kind="discard_to_four", player=p.index))
    elif t == "take_round_card":
        stack = s.end_of_round_stacks[s.round - 1]
        stack.remove(a["card"])
        p.hand.append(a["card"])
        if len(stack) == 1 and all(q.passed for q in s.players):  # the last player to pass discards the leftover card (PASS-04)
            s.discard.append(stack.pop())
    elif cards.resolve_decision(s, p, d, a, events):
        pass
    elif t == "land_free":
        _land(s, p, a, events, free=True, opts=d.data)
    elif t == "signal_where":
        if a["where"] == "tile":
            species.mark_tile(s, p, events, data=not d.data.get("nodata"))
        else:
            rewards.mark_signal(s, p, d.data["sector"], events, data=not d.data.get("nodata"), allow_tile=False)
    elif t == "orbit_free":
        _orbit(s, p, a, events, free=True, opts=d.data)
    elif t == "play_exertian":
        species.play_exertian(s, p, a["card"], d.data["cost"])
    elif t == "skip_exertian":
        pass
    elif t == "mark_objective":
        objectives.mark(s, a["objective"], a["task"])
    elif t == "take_alien":
        species.take_alien_card(s, p, d.data["slot"], a["source"])
    elif t == "choose_message":
        species.reach_message(s, p, a["hex"], events)
    elif t == "take_card":
        cid = effects.take_from_row_or_deck(s, p, a["source"])
        if d.data.get("reveal") and cid is not None:  # FAQ-C011: reveal the card and gain its free-action corner
            cards.gain_corner(s, p, cid)
    elif t == "mark_signal":
        for _ in range(d.data.get("times", 1)):
            rewards.mark_signal(s, p, a["sector"], events, data=not d.data.get("nodata"))
    elif t.startswith("scan_"):
        techs.resolve_scan(s, p, a, events)
    elif t == "place_computer_tech":
        techs.place_computer_tech(s, p, d, a["slot"])
    elif t == "place_trace":
        rewards.place_trace(s, p, a, events)
        if d.data.get("then_vp") and s.last_trace_kind != "any":  # #75: points for each trace in that color
            effects.gain_score(s, p, d.data["then_vp"] * sum(1 for _, k in p.trace_log if k == s.last_trace_kind))
    elif t == "choose_land_slot":
        _take_land_data(s, p, d.data["planet"], a["slot"])
    elif t == "choose_gold":
        next(g for g in s.gold_tiles if g.tile == a["tile"]).markers.append(p.index)
        p.gold_markers.append(a["tile"])
    if d.kind in orgs.SETUP_KINDS and not any(x.kind in orgs.SETUP_KINDS for x in s.pending):
        s.phase = "play"


# ---------------------------------------------------------------------------------------------------------------------------------
# turn flow
# ---------------------------------------------------------------------------------------------------------------------------------


def _advance(s: GameState, events: list[dict[str, Any]]) -> None:
    """Run the automatic steps of a turn until the engine needs a choice or the next player's turn begins."""
    while True:
        if not s.pending and s.stashed:  # the free action that interrupted the main action is done (FREE-00)
            s.pending, s.stashed = s.stashed, []
            s.free_active = False
        if s.pending:
            return
        s.free_active = False
        if (
            s.rival is not None
            and s.phase == "play"
            and s.stage is None
            and not s.main_done
            and s.current_player == s.rival.index
            and not s.players[s.current_player].passed
        ):
            rival.take_turn(s, events)  # SOLO-20: the rival takes its turn by itself
            continue
        if s.queue or s.playing is not None:
            cards.run_queue(s, events)
            continue
        if s.main_done and s.completed and s.stage in (None, "sectors"):
            # SECTOR-10, TURN-05, A-005 (owner, 2026-10-14): the sectors the main action completed are resolved right after it; the free
            # actions that follow cannot change them
            s.stage = "sectors"
            _resolve_completed_sector(s, events)
            continue
        if s.stage == "sectors":
            s.stage = None
            continue
        if s.stage == "pass":
            p = s.players[s.current_player]
            if not s.pass_discard_checked:  # PASS-02: only before taking the round card
                s.pass_discard_checked = True
                if len(p.hand) > 4:
                    s.pending.append(Decision(kind="discard_to_four", player=p.index))
                    return
            if not s.pass_rotated:  # PASS-03: the first player to pass rotates the solar system
                s.pass_rotated = True
                if not s.first_pass_done:
                    s.first_pass_done = True
                    _rotate(s, events)
            if not s.pass_card_asked:
                s.pass_card_asked = True
                if s.round <= 4:  # PASS-04, PASS-05: end-of-round cards exist for rounds 1 to 4
                    s.pending.append(Decision(kind="take_round_card", player=p.index))
                    return
            s.stage = "turn_end"
        elif s.stage == "turn_end":
            if s.completed:  # sectors completed after that (the rival's, a pass, a free action at the end): the same way
                _resolve_completed_sector(s, events)
                continue
            if not _resolve_milestones(s, events):
                return
            if species.resolve_discoveries(s, events):  # TURN-04: discoveries after sectors and milestones
                continue
            _next_turn(s, events)
        else:
            return


def _resolve_completed_sector(s: GameState, events: list[dict[str, Any]]) -> None:
    """TURN-05: the player chooses which completed sector is resolved next (the last one is resolved without asking)."""
    if len(s.completed) > 1 and not rival.is_rival(s, s.current_player):
        s.pending.append(Decision(kind="sector_order", player=s.current_player, data={"sectors": list(s.completed)}))
        return
    rewards.resolve_sector(s, s.completed.pop(0), events)  # one sector, or the rival's (lowest completed first)


def _rotate(s: GameState, events: list[dict[str, Any]]) -> None:
    cards.rotate_everything(s, events)


def _resolve_milestones(s: GameState, events: list[dict[str, Any]]) -> bool:
    """MILE-01 to MILE-10: resolve reached milestones at the end of the turn, current player first, clockwise, neutral last.
    Returns True when nothing is left to resolve."""
    n = len(s.players)
    order = {(s.current_player + k) % n: k for k in range(n)}
    queue = sorted(s.crossed, key=lambda c: (c[1] in NEUTRAL_MILESTONES, order[c[0]]))
    while queue:
        player, m = queue.pop(0)
        s.crossed = list(queue)
        if rival.is_rival(s, player) and m not in NEUTRAL_MILESTONES:
            if m in GOLD_MILESTONES:
                rival.choose_gold(s, events)  # SOLO-15
            elif m >= species.MESSAGE_BASE and m < species.EXERT_BASE:
                s.players[player].messages.remove(m - species.MESSAGE_BASE)
                rival.choose_message(s, events)  # SOLO-ALIEN-02
            continue
        if species.EXERT_BASE <= m < species.CARD_MESSAGE_BASE:  # ALIEN-EXE-03, ALIEN-EXE-04: an Exertian milestone
            pl = s.players[player]
            ms = s.species[species.exertian_slot(s) or 0].extra["milestones"][m - species.EXERT_BASE]
            if pl.exertian_hand and pl.credits >= ms["cost"]:
                s.pending.append(Decision(kind="exertian_play", player=player, data={"cost": ms["cost"]}))
                return False
            continue
        if m >= species.CARD_MESSAGE_BASE:  # ALIEN-CEN-02: a Centaurian card reached its marker (no free actions now)
            alien_steps.resolve_message(s, s.players[player], m - species.CARD_MESSAGE_BASE, events)
            if s.pending:
                return False
            continue
        if m >= species.MESSAGE_BASE:  # ALIEN-CEN-04: a Centaurian message milestone
            s.players[player].messages.remove(m - species.MESSAGE_BASE)
            events.append({"type": "message_reached", "player": player, "target": m - species.MESSAGE_BASE})
            s.pending.append(Decision(kind="message_reward", player=player))
            return False
        if m in GOLD_MILESTONES:
            s.pending.append(Decision(kind="gold_choice", player=player))
            return False
        _neutral_marker(s, m, events)
    s.crossed = []
    return True


def _neutral_marker(s: GameState, m: int, events: list[dict[str, Any]]) -> None:
    """MILE-05: move one nonplayer marker to the leftmost empty of the six discovery spaces (A-008, FAQ-33)."""
    key = str(m)
    if s.neutral_markers.get(key, 0) <= 0:
        return
    for slot in s.species:
        for i, occupant in enumerate(slot.discovery_spaces):
            if occupant is None:
                slot.discovery_spaces[i] = "n"
                s.neutral_markers[key] -= 1
                events.append({"type": "neutral_marker", "milestone": m, "species_slot": s.species.index(slot)})
                if all(x is not None for x in slot.discovery_spaces):
                    slot.complete = True  # ALIEN-01: revealed once the turn is over
                return


def _next_turn(s: GameState, events: list[dict[str, Any]]) -> None:
    if s.rival is not None and s.current_player != s.rival.index:
        objectives.end_turn(s)  # SOLO-OBJ-05
    s.stage = None
    s.undo, s.undo_log = None, []  # UNDO-01: nothing is taken back across turns
    s.main_done = False
    s.turn_fx = []
    s.turn_completed = False
    p = s.players[s.current_player]
    p.movement = 0  # unused movement is lost at the end of the turn (A-015)
    orgs.end_turn(s, p)
    n = len(s.players)
    for k in range(1, n + 1):
        q = (s.current_player + k) % n
        if not s.players[q].passed:
            s.current_player = q
            s.turn += 1
            return
    _end_round(s, events)


def _end_round(s: GameState, events: list[dict[str, Any]]) -> None:
    """ROUND-01 to ROUND-03: income (rounds 1 to 4), the starting player marker moves on, and the next round starts."""
    n = len(s.players)
    objectives.end_round(s, s.round, events)  # SOLO-OBJ-06, SOLO-OBJ-07: before the income
    if s.round < 5:
        for k in range(n):  # income in turn order from the starting player (fixed order keeps draws reproducible)
            p = s.players[(s.start_player + k) % n]
            if rival.is_rival(s, p.index):
                continue  # the rival has no income (A-025)
            if p.organization is not None:
                orgs.gain_income(s, p)  # EXP-ORG-08, A-031: the organization's income replaces the income card
                continue
            p.credits += 3
            p.energy += 2
            effects.draw_random_card(s, p)  # the income card's random card (INCOME-03)
            for cid in p.tucked:
                effects.gain_income_resource(s, p, tables.cards()[cid]["income"])
        s.start_player = (s.start_player + 1) % n
        s.round += 1
        s.turn = 1
        s.first_pass_done = False
        for p in s.players:
            p.passed = False
        s.current_player = s.start_player
        events.append({"type": "round", "round": s.round})
    else:
        s.phase = "finished"
        s.final_scores = scoring.final_scores(s)  # END-01 to END-03
        s.winners = scoring.winners(s.final_scores, s.rival.index if s.rival else None)
        events.append({"type": "game_over"})
