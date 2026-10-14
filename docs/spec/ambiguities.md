# Rulebook ambiguities

Agents add entries here and stop work on the affected rule (CLAUDE.md, hard rule 3). The owner rules, and the ruling is copied into the spec with its rule ID.

Entry format:

```
## A-NNN: short title
- Status: open | ruled
- Rule IDs affected:
- Rulebook page and text:
- Readings: (1) ... (2) ...
- Consequence of each reading:
- Ruling (owner) and date:
```

## A-001: Promo cards SE EN 01 and SE EN 02
- Status: ruled (the official FAQ settles the details, see FAQ-C300 in faq.md)
- Rule IDs affected: (to be assigned) setup, deck composition, Pluto, rated play
- Rulebook page and text: neither rulebook describes these cards. The repo's card text for SE EN 01 reads "Keep this card in front of you. If you have a probe in the outermost ring, you may use an orbit or land action to place that probe on Pluto." SE EN 02 ("Gateway to Mars") is a normal card with a bonus for Mars.
- Readings: (1) The promo cards are shuffled into the main deck when the option is on. (2) They are dealt or offered some other way. (3) For SE EN 01, Pluto is a new space on the board that the base rules do not define (its rewards, capacity and how it counts for scoring and for other cards).
- Consequence of each reading: changes setup, deck size (138 vs 140), and the rules for Pluto; also whether rated games may use the option.
- Questions for the owner: how do the physical promo cards say they enter the game? What does Pluto give and hold, and do orbiters and landers there count for scoring and missions? Should rated games allow the option (it changes the deck, so I suggest the option is a game setting shown to all players)?
- Ruling (owner), 2026-10-12: Both promo cards are shuffled into the main deck and are drawn and played like any other card. SE EN 01 stays in play near the player who played it and acts as a planet that the player can orbit or land on using its effect. The option to include the promo cards is a game setting shown to all players, including in rated games. Still open: what orbiting or landing on the SE EN 01 planet costs and gives (rewards, whether landers and orbiters there count for scoring and missions).
- Ruling (owner), 2026-10-12, Pluto details for SE EN 01: it has 1 orbit slot and 1 landing slot. The cost of orbiting and landing is the same as normal orbiting and landing. Only the player who played the card can orbit or land there. Orbiting gives 11 points, 3 publicity and 1 trace of any kind. Landing gives 11 points, 4 data and 1 yellow trace. From the card text in the repo, the effect lets a probe in the outermost ring use an orbit or land action to be placed on Pluto.
- FAQ confirmation (2026-10-13): the FAQ states Orbit 1 credit + 1 energy, Land 3 energy (2 with an orbiter at Pluto, less with the landing tech), 1 orbiter and 1 lander space, only the owner can use it, Pluto counts as a planet, and its orbiter and lander count for the gold tile and missions. The three points below are therefore settled. Earlier reading, now confirmed: the normal landing discount applies (an orbiter at Pluto, which can only be the owner's, makes landing cost 2 energy instead of 3); there is no 3-point first-orbiter bonus; whether orbiters and landers on Pluto count for scoring and missions (for example "at a planet", gold tile Other B) is not stated.

## A-002: Rival probe placement when neither first space is available
- Status: ruled (final: follow the rulebook, see the last ruling line)
- Rule IDs affected: SOLO-PROBE (to be assigned)
- Rulebook page and text: solo game, probe action: "If both first spaces are available, or if neither is, the rival defers to the action card instead."
- Readings: (1) "Neither is available" means both the first orbiter space and the first lander space are taken, and the rival then places in the next free space of the type the card prefers. (2) It places in the next free space of the preferred type, and if that type has no free space it uses the other type. (3) The rival does nothing and the action is skipped in favor of the next action on the card.
- Consequence of each reading: changes where the rival's probe ends up and how many points and resources it earns, so solo results differ.
- Questions for the owner: does the printed rulebook or FAQ say what the rival does when neither first space is free? What if the preferred type has no free space at all?
- Ruling (owner), 2026-10-12: When the rival did not land on a moon: if the first orbiter space is available it orbits; if not, it lands if the first lander space is available; if neither first space is available, it takes the first empty space of the action the card prefers; if the preferred action has no empty space, it takes the first empty space of the other action. Note for the spec: when BOTH first spaces are available the rulebook (p.25) says the rival follows the card's printed preference, and the owner confirmed on S.1 that it prefers the orbiter. The ruling above reads as orbit-first only when just the orbiter space is available; the spec follows the card preference when both are available. Owner to confirm this reading.
- Ruling (owner), 2026-10-12, replaces the note above: no. Even if both first spaces are free, the rival orbits first. So the order is: orbit if the first orbiter space is free; else land if the first lander space is free; if neither is free, take the first empty space of the card's preferred action, and if that has none, the first empty space of the other action.
- Conflict to resolve: this differs from the rulebook p.25 ("If both first spaces are available, or if neither is, the rival defers to the action card") and from the owner's earlier statement for S.1 ("tries to land on the first slot if both or neither first slots are available, choose based on the preference printed on the card"). Under the new ruling, the card's printed preference only matters when neither first space is free, so on the lander-preferring cards (S.7, S.8, S.12, S.13, S.17) it would never apply when both are free. Recorded as ruled; owner to confirm that this is intended.
- Final ruling (owner), 2026-10-13: follow the rulebook. After the rival's probe reaches a planet: (1) if a moon has a free space and the rival has a probe tech, it discards the tech and lands on the moon (decision arrow picks among several); (2) otherwise it takes the first orbiter space or the first lander space; (3) if both first spaces are available, or neither is, it follows the preference printed on the card (rulebook p.25), taking the first empty space of the preferred type, and if that type has no empty space, the first empty space of the other type. The earlier "orbit first even when both are free" wording is withdrawn.

## A-003: End-of-round cards
- Status: ruled
- Rule IDs affected: SETUP-17, PASS-04
- Rulebook page and text: p.5 "Prepare 4 stacks of cards. Each stack contains 1 more card than there are players." p.19: "Choose one card from this round's end-of-round cards and return the rest."
- Readings: (1) The cards come from the shuffled main deck and are face up so players can choose. (2) The cards are a separate set. (3) The cards are face down and chosen blind.
- Consequence of each reading: changes the card pool, what players see when choosing, and the deck size.
- Questions for the owner: where do the stack cards come from, and are they face up? (The art on p.5 and p.19 shows face-down cards with the main deck back.)
- Ruling (owner), 2026-10-12: The end-of-round stacks are dealt from the main deck face down and set aside during setup. A player who passes gets to see the cards of that round's stack when choosing.

## A-004: Deal order at setup
- Status: ruled
- Rule IDs affected: SETUP-13, SETUP-36
- Rulebook page and text: none; the card row and the five cards per player are dealt in unspecified order.
- Consequence: none for fairness, only for reproducibility.
- Proposed ruling: card row first, then hands in turn order starting with the first player.
- Ruling (owner), 2026-10-12: Any deal order is fine. All randomness (shuffles, disc layout, species choice, starting player) comes from a seeded random number generator so every game is reproducible.

## A-005: Completed sectors versus later free actions
- Status: ruled
- Rule IDs affected: TURN-04, TURN-05, SECTOR-10
- Rulebook page and text: p.13 "When you finish your main action, resolve all of the sectors that have been completed, in any order you choose." p.7: free actions can be taken "before, after, or even during your main action"; the turn ends once the main action and any free actions are done.
- Readings: (1) Sectors are resolved right after the main action, before the player's remaining free actions. (2) Sectors are resolved when the turn ends, after free actions.
- Consequence of each reading: free actions after the main action (placing data, discarding cards for signals, tucking income, completing missions) can change who wins a sector or what triggers.
- Questions for the owner: which reading is right? (Reading 1 follows p.13 literally; reading 2 follows p.7 and p.18.)
- Ruling (owner), 2026-10-12: Reading 1: completed sectors are resolved right after the main action, before the player's remaining free actions. No free action can change the outcome of a sector.

## A-006: Income after passing
- Status: ruled
- Rule IDs affected: PASS-01, PASS-06, INCOME-04
- Rulebook page and text: p.19 "players may resolve their income anytime after passing, even before the current round ends". Also, after the pass steps, no more free actions.
- Readings: (1) Early income is bookkeeping only, no extra free actions after passing. (2) Early income gives resources usable for free actions.
- Proposed ruling: reading 1.
- Ruling (owner), 2026-10-12: Reading 1: resolving income early is bookkeeping only; no free actions after passing.

## A-007: Disc geometry and pushed probes
- Status: ruled, and the solar system transcription is confirmed (`board-solar-system.md`)
- Rule IDs affected: ROTATE-03, ROTATE-05, BOARD-01
- Rulebook page and text: p.16 describes cutouts and pushes only in pictures.
- Questions for the owner: which spaces are cutouts, in which direction a pushed probe moves, and what happens if the next space is occupied. The board definition will be written from the board images and the owner should verify it.
- Ruling (owner), 2026-10-12: The owner will come back to this later.

## A-008: Neutral milestone placement
- Status: ruled
- Rule IDs affected: MILE-05
- Rulebook page and text: p.18 "If any of these is empty, move a nonplayer marker from the milestone to the leftmost empty space."
- Readings: (1) The leftmost empty space of the two species' six discovery spaces taken together, in board order. (2) The triggering player chooses a species. (3) The nonplayer takes the species with fewer markers.
- Consequence of each reading: which species gets closer to discovery.
- Ruling (owner), 2026-10-12: Reading 1: consider all six discovery spaces together and fill the first empty one, from left to right.

## A-009: Nonplayer markers used per milestone crossing
- Status: ruled
- Rule IDs affected: SETUP-20, MILE-05
- Rulebook page and text: p.5 and p.18: two nonplayer markers per neutral milestone in 1 to 2 player games, one in 3 player games.
- Readings: each crossing by a player uses one marker, or each turn that crosses uses one marker.
- Proposed ruling: each player's crossing uses one marker.
- Ruling (owner), 2026-10-12: Each player's crossing of a neutral milestone uses 1 nonplayer marker.

## A-010: Which cards are the advanced rival cards
- Status: ruled
- Rule IDs affected: SOLO-05, SOLO-06
- Rulebook page and text: p.22 "randomly select one advanced action card (S.5-S.15)". The card art shows S.15 is the Mascamites species card.
- Readings: the advanced cards are S.5 to S.14 and the rulebook has a typo, or S.15 is also an advanced card.
- Proposed ruling: S.5 to S.14.
- Ruling (owner), 2026-10-12: The advanced rival cards are S.5 to S.14. (The rulebook's "S.5-S.15" is a typo: S.15 is the Mascamites species card.)

## A-012: Rival runs out of advanced cards
- Status: ruled
- Rule IDs affected: SOLO-12
- Rulebook page and text: p.23 the rival gains an advanced card each time its progress marker crosses the growth icon. Nothing is said about running out.
- Ruling (owner), 2026-10-12: When there are no advanced action cards left to add, nothing happens.

## A-013: Tucking a card with no cards in hand
- Status: ruled
- Rule IDs affected: INCOME-02
- Rulebook page and text: p.6 "tuck a card from your hand".
- Proposed ruling: with an empty hand the effect is lost.
- Ruling (owner), 2026-10-12: Proposed ruling accepted: if the hand is empty when a tuck-for-income effect occurs, the effect is lost.

## A-014: Rival and Mascamite samples or anomalies
- Status: ruled
- Rule IDs affected: SOLO-ALIEN-04
- Rulebook page and text: the Mascamites and Anomalies rule sheets have no solo rules.
- Questions for the owner: does the rival interact with samples, capsules or anomalies other than through S.15 and S.16 (for example by marking a blue space holding a sample token)?
- Ruling (owner), 2026-10-12: The rival interacts with Mascamite samples and anomalies only through its action cards (S.15 and S.16).

## A-015: Unused movement at the end of a turn
- Status: ruled
- Rule IDs affected: MOVE-01
- Rulebook page and text: movement points come from the Move Energy / card effects and are spent by moving probes.
- Proposed ruling: unused movement points are lost when the turn ends; they do not carry to the next turn.
- Ruling (owner), 2026-10-13: Proposed ruling accepted: unused movement points are lost at the end of the turn.

## A-016: Landing on a moon, first-lander data and planet landers
- Status: ruled
- Rule IDs affected: LAND-04, LAND-05
- Rulebook page and text: p.11 "The first player to land on a planet also receives data"; p.11 and p.17 "When landing on a moon the player gains the rewards depicted at the moon".
- Readings: (1) a moon landing gives only the moon's rewards, takes no first-lander data space and does not count as a lander on the planet; (2) it also gives the planet's landing rewards and data.
- Proposed ruling: reading 1.
- Questions for the owner: confirm reading 1. Also confirm that a moon lander does not count as a "lander at the planet" for cards, gold tiles and the cost of landing.
- Ruling (owner), 2026-10-13: Reading 1. Landing on a moon gives only the moon's rewards, not the planet's landing rewards. (Not addressed by the owner, so unchanged in the engine: a moon lander takes no first-lander data space and is not counted as a lander on the planet itself; it does count for missions that include moons, FAQ-C058.)

## A-017: Counting traces by kind, and "spaces from Earth"
- Status: ruled
- Rule IDs affected: CARD-46, LIFE-01, LIFE-04; cards #87 Project Longshot and all trace-counting cards (#64, #66, #70, #96, #97, #105, #62, #63, #68)
- Rulebook page and text: p.28 "You have a life trace of a kind: a trace of that kind you have marked"; #87 "Have a probe at least 5 spaces from Earth".
- Readings: (a) A trace placed on a discovery space counts as the kind of that space's color. A trace placed on an overflow space counts as the kind it was gained as (yellow from a landing, blue from Analyze), and a universal (any) trace placed on an overflow space counts as no particular kind. (b) Overflow markers count as no kind at all. (c) "Spaces from Earth" is the number of single-space moves between the probe and Earth's space (shortest path, never through the Sun).
- Proposed ruling: (a) and (c).
- Questions for the owner: confirm (a) or choose (b); confirm how #87 counts spaces (path of moves, or another measure).
- Ruling (owner), 2026-10-13: (a) and (c) with one change: count all of the player's colored markers on the species and discovery board slots. A trace counts for the color of the space it is placed on, whatever kind of trace it was gained as. (Overflow spaces are colored too, see A-022.) (c) Spaces from Earth are counted as the shortest path of moves.

## A-018: Cards that remove an orbiter or lander (#15, #84)
- Status: ruled
- Rule IDs affected: ORBIT-04, LAND-04, FAQ-C015, FAQ-C084
- Rulebook page and text: #15 "Remove one of your orbiters from any planet"; #84 "Remove one of your landers from any planet or moon"; FAQ says that if the figure on the first space is removed, that space is free again and the next one to take it gets the bonus.
- Questions for the owner: when the player has several orbiters (or landers) at the planet, may the player choose which one to remove, including the one on the first space? Does the card's own player's first-orbiter marker matter if another player's figure sits on the first space?
- Ruling (owner), 2026-10-13: The player may freely choose which of their own orbiters or landers to remove.

## A-019: A mission card and its own effect
- Status: ruled
- Rule IDs affected: CARD-12
- Rulebook page and text: p.15 "Only things done after the mission was played can trigger it."
- Readings: (1) the card is in play once its effect is finished, so what its own effect does (for example #117 Lunar Gateway's free launch) cannot cover a circle of that card; (2) the card is in play from the moment it is played, so its own effect can trigger it.
- Proposed ruling: reading 1.
- Questions for the owner: confirm reading 1 or choose reading 2.
- Ruling (owner), 2026-10-13: Reading 2. A mission is in play from the moment its card is played, so the card's own effect (and the cost paid to play it) can trigger it.

## A-020: Where discarded alien cards go
- Status: ruled
- Rule IDs affected: PLAY-02, CARD-30, RES-04, ALIEN-04
- Rulebook page and text: p.15 "place the card face up in the discard pile"; Centaurian rule sheet "cards that don't become income are simply discarded per usual". Nothing says whether an alien card has a discard pile of its own.
- Readings: (1) alien cards are discarded onto the one discard pile, and when the main deck runs out that pile (alien cards included) is reshuffled into the main deck (RES-04); (2) each species has its own discard pile that is never reshuffled into the main deck.
- Proposed ruling: reading 1 (the literal "per usual").
- Questions for the owner: confirm reading 1 or choose reading 2. Reading 1 means alien cards can be drawn later from the main deck.
- Ruling (owner), 2026-10-13: Reading 1. Alien cards are discarded onto the one discard pile and are reshuffled with it (the main deck is not expected to run out in practice).

## A-021: Data taken from the 'Oumuamua tile
- Status: ruled
- Rule IDs affected: ALIEN-OUM-03, ALIEN-OUM-04
- Rulebook page and text: rule sheet 5-6: "Place 3 data tokens in the data slot of the 'Oumuamua tile"; "mark it either in the sector or on the 'Oumuamua tile"; the tile is "completed by taking the last data in its slot".
- Readings: (1) a marker placed on the tile takes the leftmost data token into the player's data pool, as in a sector (SECTOR-01); (2) the data tokens only count the markers and nobody gains them.
- Proposed ruling: reading 1 (the sheet speaks of "taking" the data).
- Questions for the owner: confirm reading 1.
- Ruling (owner), 2026-10-13: Reading 1. The 'Oumuamua tile, once placed on disc 3, acts as a sector: players mark signals on it and take its data.

## A-022: Overflow markers on the "Other" gold tile, side A
- Status: ruled
- Rule IDs affected: END-16, LIFE-02, A-017
- Rulebook page and text: p.21 "for each set of three life traces, one of each color; markers on the overflow space count". Ruling A-017 says an overflow marker has no color.
- Readings: (1) an overflow marker counts as a wildcard that completes a set in place of a missing color; (2) overflow markers count as traces but, having no color, can never complete a set (so the rulebook sentence would have no effect); (3) three overflow markers make a set on their own.
- Proposed ruling: reading 1 (a set needs one trace of each color, and an overflow marker may stand for any one of the three colors).
- Questions for the owner: confirm reading 1 or choose another.
- Ruling (owner), 2026-10-13: None of the proposed readings. Overflow markers have colors: each overflow space belongs to a color, and a marker counts for the color of the slot it sits on. This also corrects my reading of A-017: overflow markers are colored too.

## A-023: What happens to the rival's action cards between rounds
- Status: ruled
- Rule IDs affected: SOLO-RIVAL-01, SOLO-19, SOLO-12
- Rulebook page and text: p.24 the rival reveals the top action card each turn and passes when no cards are left (p.26); p.23 a new advanced card goes on top and "will come up on the rival's next turn (unless the rival has already passed for that round)". Nothing says when the used cards come back.
- Proposed ruling: at the end of every round all of the rival's action cards (used and unused, including the ones added by growth and the species cards) are shuffled into a new face-down deck.
- Questions for the owner: confirm, or say how the deck is refreshed.
- Ruling (owner), 2026-10-13: Yes. The rival's used action cards are shuffled back into its deck after it passes.

## A-024: Details of the rival's choices
- Status: ruled
- Rule IDs affected: SOLO-RIVAL-02, SOLO-RIVAL-07, SOLO-RIVAL-09, SOLO-ALIEN-03, FAQ-57
- Readings: (1) the leftmost and rightmost moon are in the order Io, Europa, Callisto, Ganymede at Jupiter and Enceladus, Titan at Saturn (the order of the planetary board art); (2) the 1st and 2nd alien species of cards S.3 and S.4 are the left and right species slots; (3) S.15 takes a random sample from Jupiter and Saturn together; (4) in the solo game the rest of the Exertian deck is kept for the rival's S.19 instead of going back to the box (FAQ-57 says it plays a random card from the deck); (5) the rival never rolls its own start: the rival is the second player (index 1).
- Questions for the owner: confirm each, in particular (1) from the physical board.
- Ruling (owner), 2026-10-13: (1) The moons from left to right are Callisto, Ganymede, Europa, Io at Jupiter and Titan, Enceladus at Saturn. (2) The first alien species is the left one. (3) No: the rival takes the sample only from the planet it targeted (S.15 takes it together with its landing there). (4) and (5) Yes.

## A-025: The rival has no income and no starting cards
- Status: ruled
- Rule IDs affected: SOLO-10, SETUP-30 to SETUP-38, ROUND-01
- Rulebook page and text: p.22 "Set up the game as you normally would for two players"; p.23 the rival does not keep track of credits, energy and cards.
- Proposed ruling: the rival gets no starting hand, no starting resources and no income at the end of a round (nothing for credits, energy or the income card's card), and its 5 starting cards stay in the deck.
- Questions for the owner: confirm.
- Ruling (owner), 2026-10-13: Yes. The rival never has any resources; every resource it would gain becomes progress on the track at 1 to 1.
