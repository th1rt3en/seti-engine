# Board, sectors and signals

Source: base rulebook pp. 4, 5, 8 to 13, 28. Rules about what happens are written here; the board's layout (coordinates, rewards, slot sizes) is data and is listed as data tasks.

## Board data (not in the rulebook text)

The rulebook describes the board by pictures. The engine's board definition must be written from the board images in `assets/` and checked by the owner against the physical board. Each item below is a data task for Phase 2, blocked on owner verification:

- **BOARD-01** The 3 discs and the Sun: ring and space structure (spaces per ring, adjacency, which spaces are comets, asteroids, planets, Earth), including the cutouts used by ROTATE-03. Transcribed in `board-solar-system.md` and confirmed by the owner on 2026-10-12.
- **BOARD-02** The set of legal initial configurations of the discs and sector boards (how the 8 sectors line up, rotation offsets). The rulebook says only that the discs must line up into eight well-defined sectors with one nearby star in each, and offers a random-layout generator (QR code `cge.as/seti-solarsystem`).
- **BOARD-03** The 8 nearby stars and their data slots: names (Kepler 22, Proxima Centauri, Sirius A, Barnard's Star, Procyon, Vega, 61 Virginis, Beta Pictoris), sector color of each (each of 4 colors appears twice: SCAN-03), slot capacity (some stars hold more than others: SETUP-15), the rewards printed along each slot (second position gives 2 points: SECTOR-03), and the winner rewards beside each star (first winner gets a greater reward than later winners).
- **BOARD-04** Publicity icons on spaces (MOVE-05), the visit rewards of planets, comets and other objects.
- **BOARD-05** Planetary board: for each planet: orbit bonuses, lander bonuses, first-lander data space (Mars has two), and each moon's reward; the order of planets is Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune.
- **BOARD-06** Tech board: positions of 12 stacks and the rotation counter spaces.
- **BOARD-07** Publicity track 0 to 10 and score track 0 to 99 (and beyond, see MILE-04), with the milestone spaces 20, 25, 30, 50, 70.
- **BOARD-08** Player board: probe and telescope tech slots, computer top-row spaces and their effects (publicity space, income space), data pool, the analyze action slot.

## Signals and sectors

- **SECTOR-01** (p.13) To mark a signal in a sector: take the leftmost data token from that sector's data slot, put it in the player's data pool, and replace it with a marker of the player's color.
- **SECTOR-02** (p.13, p.14) If the data pool already holds 6, the excess data is discarded (RES-01). The marker is still placed.
- **SECTOR-03** (p.13) If a marker is placed in the second position of a sector's data slot, the player immediately scores 2 points.
- **SECTOR-04** (p.13) Data is replaced by markers in order from left to right.
- **SECTOR-05** (p.13) If a player can place more markers than the slot can hold, that is allowed. The player gets no data for excess markers, but they count towards winning the sector once it is completed.
- **SECTOR-10** (p.13) If a marker replaces the last data token in the slot, the sector is completed. All sectors completed during a main action are resolved after the main action is finished, in any order the player chooses (TURN-05).
- **SECTOR-11** (p.13) Winner: the player with the most markers in the data slot wins the sector. They place a marker on the space beside the nearby star and gain the reward shown there. A tie for most markers is broken in favor of the player whose marker was placed later.
- **SECTOR-12** (p.13) Each player who contributed at least 1 marker (including the winner) gains 1 publicity.
- **SECTOR-13** (p.13) Reset: after determining the winner, determine second place with the same tiebreak. The second-place player (if there is one) leaves one marker on the first space of the sector's data slot. All other markers in the slot return to their players. The emptied spaces are refilled with data tokens from the supply. If all markers belong to one player, there is no second place (p.28).
- **SECTOR-14** (p.13, p.28) The winner's marker beside the star stays for the rest of the game, because some cards reward sectors the player has won. When determining a sector's next winner, ignore that marker. It does not help to win again (p.28).
- **SECTOR-15** (p.13) A sector can be completed and won again later. Rewards differ by order of winning (BOARD-03).
- **SECTOR-16** (p.13) The winner's reward can include a life trace (for example the pink trace space on the example sector): see LIFE-01.
- **SECTOR-20** (p.28) "Win a sector" for card terms: a win in a sector (any color), or a win in a sector of a given color. When counting sector wins every marker beside a star counts, even several in the same sector (p.21).
- **SECTOR-21** (p.20, p.28) A "signal in a sector of a color": mark a signal matching that color: one of the two sectors of that color. "Mark a signal" without more detail: the card specifies where.
- **SECTOR-22** (p.12) A card's sector color (upper-right corner of the card) is the color of the two sectors where a signal marked by discarding that card goes.
