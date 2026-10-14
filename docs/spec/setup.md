# Setup

Source: base rulebook pp. 4 to 6 and 28 (setup reminders). Applies to the base game, 2 to 4 players. Solo setup is in `solo.md`. Page numbers are the printed rulebook page numbers.

## Components and counts

- **SETUP-01** (p.2, p.4) The main board has three parts: the planetary board, the solar system board and the tech board. The solar system board has 3 rotating discs in the middle, a Sun in the center, and 4 sector boards around the discs.
- **SETUP-02** (p.2) Each player color has: 1 player board, 8 figures, 30 markers, 1 publicity counter, 1 score counter, a 100/200-point token and 1 income card. Figures and markers are interchangeable for the same color (p.2). There is no limit to the number of markers a player may have; if a player runs out, use a replacement (p.28).
- **SETUP-03** (p.3) General pieces: 48 tech tiles (12 stacks of 4), 4 double-sided gold scoring tiles, 12 two-point tiles, a main deck of 138 cards, 1 starting player marker, 30 credit tokens, 30 energy tokens, 2 solar system rotation tokens, 70 data tokens. Credits, energy, data and markers are unlimited (replace if short).

## Game setup

- **SETUP-10** (p.4) Assemble the main board and place it in the middle of the table.
- **SETUP-11** (p.4) Alien species: shuffle the 5 alien species boards face down and place 2 of them at random in the slots on the edge of the planetary board. Return the other 3 to the box without looking at them. All alien cards and other alien components stay out of the game until their species is discovered (see `aliens.md`). Which two species are in play is hidden information until discovery.
- **SETUP-12** (p.4) Solar system board: the 3 discs and the 4 sector boards start in a random configuration, subject to: the discs line up to form eight well-defined sectors, with one nearby star in each sector. (The rulebook offers a QR layout generator or manual randomizing; the engine must produce a random legal configuration from the seed. The set of legal configurations is a data question, see `board-and-sectors.md` BOARD-02.)
- **SETUP-13** (p.4) Card row: shuffle the main deck and deal 3 cards face up to form the card row.
- **SETUP-14** (p.4) Credit and energy tokens are kept in supply near the board.
- **SETUP-15** (p.4) Data: each nearby star receives enough data tokens to fill its data slot. The number differs per star; see `board-and-sectors.md` BOARD-03. The remaining data is the supply.
- **SETUP-16** (p.5) Technologies: there are 12 technologies (4 in each of 3 colors: probe, telescope, computer). For each technology, shuffle its 4 tech tiles and place them as a stack on the matching space of the tech board with the technology side face down. Place a 2-point tile on top of each of the 12 stacks.
- **SETUP-17** (p.5) End-of-round cards: prepare 4 stacks of cards. Each stack contains 1 more card than the number of players. (Example: 4 cards per stack in a 3-player game.) After passing in rounds 1, 2, 3 or 4, a player gains a card from that round's stack (see PASS-03). The rulebook does not say where these cards come from or whether they are face up: open question A-003.
- **SETUP-18** (p.5) Solar system rotation tokens: place one token on the marked space on the tech board (the rotation counter). Place the second token on the first stack of end-of-round cards (the reminder to rotate the solar system the first time a player passes in a round).
- **SETUP-19** (p.5) Gold scoring tiles: place the 4 double-sided tiles beside the board, each with a random side up.
- **SETUP-20** (p.5, p.18, p.28) Neutral milestones: place neutral markers (of an unused color) above the 20-point and 30-point spaces of the scoring track. 1 or 2 players: 2 markers above each of the two spaces. 3 players: 1 marker above each space. 4 players: neutral milestones are ignored.
- **SETUP-21** (p.5, p.20) Neutral markers also take part in species discovery in games with fewer than 4 players (see MILE-05 and ALIEN-02).

## Player setup

- **SETUP-30** (p.6) Each player picks a color and takes the matching pieces.
- **SETUP-31** (p.6) The starting player is the player who last saw a UFO. The engine chooses the starting player at random from the seed (or lets the creator choose: a game option decided in Phase 4). The starting player takes the starting player marker. Players play in clockwise order.
- **SETUP-32** (p.6, p.28) Starting score: 1 point for the first player, 2 for the second, 3 for the third, 4 for the fourth.
- **SETUP-33** (p.6) Each player takes the starting income card of their color. The back of the card shows the starting resources: 4 publicity, 4 credits, 3 energy and 5 cards.
- **SETUP-34** (p.6) Publicity: each player's publicity counter starts on space 4 of the publicity track. The track runs from 0 to 10 (SETUP-37).
- **SETUP-35** (p.6) Credits and energy: each player takes 4 credit tokens and 3 energy tokens.
- **SETUP-36** (p.6) Cards: each player draws 5 cards from the deck, then turns one of them into income (see FREE-10 and INCOME-01): tuck one card from hand under the starting income card and immediately gain the resource printed in its bottom-right corner (INCOME-02).
- **SETUP-37** (p.6, p.28) Publicity is capped at 10: if a player has 10 publicity, ignore effects giving more.
- **SETUP-38** (p.6) The starting income card also gives income in later rounds (rounds 2 to 5): 3 credits, 2 energy and 1 random card, which the engine treats as the base income (see INCOME-03). Setup resources are not repeated in round 1.

## Setup order of operations

The rulebook lists setup items by number; the engine performs them in this order: SETUP-10 to 21 (table), then SETUP-30 to 38 (players). The deck is shuffled once before the card row is dealt; each player's 5 cards are then drawn from the same deck, in turn order starting with the first player.

Open: the deck order in which the card row and the players' hands are dealt is not specified. It matters only for reproducibility, not for fairness (the order is random), so it is a design choice for the engine, not a rule: A-004.
