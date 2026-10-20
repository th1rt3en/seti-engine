"""What a seat knows about the other seats' hands from what happened in public: the cards they took from the display and the cards they showed.

The other seat's hand is otherwise not seen: the agent gets only its size. A card that the other seat took from the display was seen by everybody when it
was taken, and a card shown through an effect (for example Pre-launch Testing) was named in the log; the seat knows that those are in the hand until the
other seat plays or discards them face up. Cards that were drawn from the deck, kept from a draw or tucked face down stay unknown. This is the same
information that a player who watches the table has; it is a list of cards, kept by the arena (and, when a bot is served, by the Worker from the action log).
"""

from __future__ import annotations

from typing import Any

PUBLIC_REMOVAL = {"play_card", "discard_free", "discard", "cover", "discard_corner", "complete_mission"}  # the card is named when it leaves the hand


class Knowledge:
    def __init__(self) -> None:
        self.known: dict[int, list[str]] = {}

    def update(self, seat: int, action: dict[str, Any], events: list[dict[str, Any]]) -> None:
        """Take in one step: the cards that were taken from the display or shown are known to be in that seat's hand; a card played or discarded is gone."""
        card = action.get("card")
        if action.get("type") in PUBLIC_REMOVAL and isinstance(card, str) and card in self.known.get(seat, []):
            self.known[seat].remove(card)
        for e in events:
            if e.get("type") == "take_display_card" and isinstance(e.get("card"), str):
                self.known.setdefault(int(e["player"]), []).append(e["card"])
            elif e.get("type") == "show_card" and isinstance(e.get("card"), str):
                held = self.known.setdefault(int(e["player"]), [])
                if e["card"] not in held:
                    held.append(e["card"])

    def of(self, seat: int) -> list[str]:
        return list(self.known.get(seat, []))
