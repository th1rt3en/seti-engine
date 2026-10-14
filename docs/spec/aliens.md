# Alien species (base game)

Source: base rulebook p.20 and the owner-supplied `docs/rules/SETI_Alien_rule_sheets_(EN).pdf` (five species: Mascamites, Anomalies, 'Oumuamua, Centaurians, Exertians). The rule sheets say which of these 5 are in a game (2 chosen at random: SETUP-11). Species board rewards, planet spaces and card data are data, not rules, and are listed as data tasks at the end. The Space Agencies species (Amoeba, Glyphids, Arkhos) are not part of this file (PLAN.md D22).

## Discovery

- **ALIEN-01** (p.20) A species is discovered when all three of its discovery spaces are filled by markers (nonplayer markers count). If it happens during a player's turn, the discovery is resolved after the turn finishes; milestones are resolved first. Steps: (1) flip the species board to reveal the species; (2) read the rule sheet; (3) follow the species' setup rules; the players who marked the three discovery spaces are rewarded at this time.
- **ALIEN-02** (p.18, p.20) In 2- and 3-player games nonplayer markers can fill discovery spaces (MILE-05). They can play only on the six discovery spaces below the boards and never block a space on the species board itself.
- **ALIEN-03** (p.20) After discovery, life traces can be marked on any empty space of the matching color on the species board (LIFE-04).
- **ALIEN-04** (p.20) Each species has a special deck of alien cards, slightly stronger than regular cards. They can be obtained only from the species. In hand they follow the rules of regular cards (CARD-32).
- **ALIEN-05** (p.20) The species' icon on a species board space lets a player draw a card of the species: from the top of the deck, or take the face-up card and replace it with the top card (for Mascamites, Anomalies, 'Oumuamua and Centaurians). These cards can be tucked for income or discarded for their free action, and they count towards the hand limit.
- **ALIEN-06** (rule sheets) When a species is discovered, shuffle its deck and deal cards to the players who marked the three discovery spaces: 1 card per marker. Keep the deck near the board and turn the top card face up beside it. (Exertians differ: ALIEN-EXE-01.)

## Mascamites

- **ALIEN-MASC-01** (sheet 1) Setup on discovery: shuffle the 7 sample tokens face down; deal 3 to Jupiter and 3 to Saturn on the solar system board; turn the remaining token face up and place it on its designated space on the species board. (The sample faces and their rewards are data.)
- **ALIEN-MASC-02** (sheet 1) Collecting samples: only possible with a card that lets the player do so. Some Mascamite cards let the player land on a planet or moon and collect a sample: look at all sample tokens on that planet's space, choose 1, return the others. The player stacks one of their markers on the chosen sample: this stack is a sample capsule that starts on the space the token was taken from. A player can land with such a card on a planet with no samples; the card stays in front of the player in case it can be completed in the future.
- **ALIEN-MASC-03** (sheet 2) Moving samples: whenever the player could move a probe, they may move a sample capsule instead. It gains publicity when moving to marked spaces and pays the asteroid penalty. It counts as a probe for all card and tech effects but cannot become an orbiter or a lander and does not count towards the probe limit. A player may have several capsules.
- **ALIEN-MASC-04** (sheet 2) Delivering samples: while a capsule is at the destination of one of the player's Mascamite mission cards, the player may deliver it as a free action, completing the mission. Remove the capsule, reveal the token, gain the reward on it, keep the card as a completed mission, and place the used token face up in the next dedicated space on the species board, where it becomes a new blue space.
- **ALIEN-MASC-05** (sheet 2) With several capsules and cards, the player chooses which card is resolved by a delivery. A blue space holding a sample token can be marked by any player like any other blue space; the marker gains the sample's reward.

## Anomalies

- **ALIEN-ANO-01** (sheet 3) Setup on discovery: place the 3 anomaly tokens, random side up, on the solar system's outermost ring: one in the sector with Earth, one 3 sectors counter-clockwise from Earth, one 3 sectors clockwise from Earth (owner re-confirmed against the rulebook, 2026-10-14). Which color goes where is seeded random. The placement is written to the log (event `anomalies_placed`). A token placed on a space with Neptune or Uranus must not cover the planet.
- **ALIEN-ANO-02** (sheet 4) Whenever the solar system rotates, check whether Earth is now in the same sector as an anomaly. If so, resolve the anomaly immediately. Each resolution is written to the log (event `anomaly`: sector, color, face, reward, winner).
- **ALIEN-ANO-03** (sheet 4) Each anomaly corresponds to one of the 3 life trace colors. Look at the column of that color on the species board: the player who has marked the highest space in that column gains the reward shown on the anomaly. If no space in the column is marked, nobody gains it. Markers below the species board (overflow) do not count.
- **ALIEN-ANO-04** (sheet 4) There is no bonus for visiting Anomalies with probes.
- **ALIEN-ANO-05** (sheet 4) The top space of a column gives only 2 points but is always available; players who mark it later are placed above those who marked it earlier.

## 'Oumuamua

- **ALIEN-OUM-01** (sheet 5) Setup on discovery: place the 'Oumuamua tile in the depicted space of disc 3 (if a probe is on that space, set the probe on top and that player gains 1 publicity immediately). Place 3 data tokens in the tile's data slot. Set the 17 exofossil tokens beside the species board.
- **ALIEN-OUM-02** (sheet 6) Exofossils: some species board spaces gain 1 exofossil token; some need exofossils to be marked (cannot mark without enough). The topmost spaces can be marked any number of times by all players, with an exofossil each time.
- **ALIEN-OUM-03** (sheet 6) Signals in 'Oumuamua's sector: when a player marks a signal there they may mark it either in the sector or on the 'Oumuamua tile. The "signal in a sector with 'Oumuamua" icon allows the same choice. There is a 1-point and a 2-point reward for placing the first and third markers in the tile's data slot.
- **ALIEN-OUM-04** (sheet 6) 'Oumuamua is completed by taking the last data in its slot: each player who marked it gains 1 exofossil. No winner is determined. The tile is fully refilled with data, leaving no markers behind.
- **ALIEN-OUM-05** (sheet 6) 'Oumuamua counts as a planet for cards that refer to planets. Each visit with a probe gives publicity. A lander or orbiter can be placed on it like on other planets.

## Centaurians

- **ALIEN-CEN-01** (sheet 7) Setup on discovery: each player takes a message tile of their color and places it as a milestone 15 points ahead of their current position on the scoring track.
- **ALIEN-CEN-02** (sheet 8) Centaurian cards cost energy, not credits. When a Centaurian card is played for its effect, the player places one of their markers 15 points ahead of their score counter, resolves the white part of the card, and keeps it in front of them. When they reach their marker, they resolve the green part of the card. Some Centaurian cards turn themselves into an unusual type of income: after tucking, gain 1 of the depicted resource immediately; those that do not become income are discarded. Centaurian cards are not missions, so they never count towards the Mission gold scoring tile. Placing and reaching markers are written to the log (events `messages_placed`, `message_card_placed`, `message_resolved`).
- **ALIEN-CEN-03** (sheet 8) With several messages in play, stack the pending message cards with the oldest on top; resolve them in the order sent.
- **ALIEN-CEN-04** (sheet 8) Reaching the message milestone: the player chooses one available reward on the species board and covers it with the milestone tile, making it unavailable to others. Milestones are resolved at the end of the turn in which they are reached or passed (MILE-01); no free actions are played at that time. The prompt lists the unclaimed rewards with what each pays; the choice is logged (events `message_reached`, `message_reward`).
- **ALIEN-CEN-05** (sheet 8) Paying data: some spaces on the board have a cost paid by discarding data from the data pool (not from the computer). A player who cannot pay cannot mark the space. The topmost spaces can be marked any number of times with 1 data each time.

## Exertians

- **ALIEN-EXE-01** (sheet 9) On discovery: shuffle the deck and deal 3 cards to each player; each player who marked a discovery space also gets 1 card per marker. Return the remainder of the deck to the box. Each player may now play one Exertian card for every marker they placed on discovery spaces. Cards are played face down and are not revealed until the end of the game.
- **ALIEN-EXE-02** (sheet 9) Exertian cards are not considered to be in hand: they are ignored for hand size and cannot be discarded in any way. They are not missions or end-of-game scoring cards.
- **ALIEN-EXE-03** (sheet 9) Milestone tiles: place one milestone tile on the scoring track 20 points ahead of the leading player's marker, and the other 40 points ahead. When a player crosses an Exertian milestone they may choose one of their Exertian cards and play it face down, even if they marked no life traces for this species.
- **ALIEN-EXE-04** (sheet 10) At the second milestone, playing an Exertian card costs 1 credit. A player without a credit cannot play it, and cannot pay for that milestone later.
- **ALIEN-EXE-05** (sheet 10) Every player gets at least 3 cards and at least 2 opportunities to play one; a player who marked 1, 2 or 3 discovery spaces gets that many extra cards and immediate opportunities.
- **ALIEN-EXE-06** (sheet 10) Danger: each Exertian card has a danger from 0 to 9. A played card adds its danger, hidden from other players until the end. Marking spaces on the Exertian board adds danger: 3 per marker on the bottom tier, 2 on the middle tier, 1 on the top tier. If the player fulfils the card's condition, they also gain its victory points at the end of the game.
- **ALIEN-EXE-07** (sheet 10) End of game: all played Exertian cards are revealed and their danger is added to the danger from markers on the board. The player with the most danger loses one-tenth of their total points, rounded down (168 points lose 16). The others lose nothing. If several players tie for most danger, all of them lose points. This is calculated after all other points have been scored, including points from the Exertian cards.

## Data tasks for the aliens (not rules)

- **ALIEN-DATA-01** For each species: the board's spaces, colors, rewards, costs, cost-to-mark and the three discovery spaces' printed rewards (discovery rewards are the "rewarded at this time" in ALIEN-01).
- **ALIEN-DATA-02** For each species: its cards (card data and verified differences in `card-verification-summary.md`), tokens and their faces (Mascamite samples, Anomaly tokens, exofossil tokens, message tiles, Exertian milestone tiles).
- **ALIEN-DATA-03** The 7 Mascamite samples and their rewards; the 'Oumuamua tile's data slot rewards; Exertian card danger and scoring formulas (owner's notes for ET.41 to ET.55).
