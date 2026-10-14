# Solo mode: rival action cards

Status: draft for owner review. The card transcription comes from the card art (`assets/solo-rival-action-cards-sheet.png`); the action rules come from the base rulebook, solo game, pages 23 to 26. Both replace the repo's solo data, which is incomplete and has errors (see the end of this file). Rule IDs are provisional.

## How the rival takes a turn (SOLO-RIVAL-01)

Reveal the top action card of the rival's deck. The rival performs one of the actions shown on the card: the top one if possible, the second if not, and so on. It is always possible for the rival to perform one of the actions on the card. After the action the turn ends. If the rival starts a turn with no cards left in its action deck, it passes (see SOLO-RIVAL-10).

## Decision arrow (SOLO-RIVAL-02)

The arrow at the top of the card points left or right. Whenever the rival has a choice between equal options, it takes the leftmost option when the arrow points left and the rightmost when it points right. This applies to: gold scoring tiles (if several tiles have their first slot free), card-row signals, moons, and life trace columns.

## Deck tiers (SOLO-RIVAL-03)

S.1 to S.4 are the 4 basic action cards of the rival's starting deck (the lighter cards). S.5 to S.14 are the advanced action cards. Each time the rival's progress marker crosses the growth icon, one random advanced card is added face down on top of the rival's action deck. S.15 to S.19 are species cards: when that species is discovered, the card S.3 or S.4 that checks for it is replaced by the species' card (SOLO-RIVAL-09).

## Actions

**Analyze (SOLO-RIVAL-04).** Only possible when the rival's computer is full, otherwise skip to the next action. Remove all data from the rival's computer (not the data pool) and give the rival the benefit shown on the card (on some cards 3 VP, printed before the "+"). The rival also gains the life trace shown on its player board. If the rival then has data in its data pool, it moves as much as possible into its computer, gaining the benefit of each space it covers. Finally, if the rival has a computer (blue) tech, it discards one and gains 3 VP and 1 progress (never more than one tech, even with several).

**Launch (SOLO-RIVAL-05).** Place a rival probe figure on Earth and gain the publicity shown (1). Some cards also advance the progress marker 1 space. If the rival already has a probe on Earth, skip this action.

**Tech (SOLO-RIVAL-06).** The rival spends 6 publicity to research a tech (skip the action if it has fewer than 6). Some cards show the action without the 6 publicity cost. Whenever the rival gains a tech, advance the solar system as usual. Some cards also advance the progress marker 1 space. The tech is chosen by the progress track: look at the rival's current position, which shows its preferred tech; if that tech has a 2-point tile on it, take it; otherwise check the next tech along the track until one with a 2-point tile is found. If none has a 2-point tile, take the first available tech by the marker. Give the rival the bonuses on the tile, including the 2-point bonus, except that it never gets the launch-a-probe bonus or the 2-data bonus (the rulebook's exception, shown by two icons).

**Probe: orbiter / lander (SOLO-RIVAL-07).** Move the rival's probe from Earth to a planet. Check the planets in the order printed (left to right) until one can be reached in the depicted number of moves; leaving an asteroid field costs 1 extra move. If no planet is reachable or the rival has no probe on Earth, skip this action. After moving, give the rival the publicity for visiting planets and comets; if several flight plans work, choose the one with the most publicity. Then the probe becomes a lander or an orbiter:
1. If the planet has a moon with a free space, the rival first tries to discard a probe (orange) tech to land on the moon. With several free moons, use the decision arrow.
2. If it does not land on a moon, the rival tries the first orbiter space or the first lander space of the planet.
3. If both first spaces are free, or neither is, the rival follows the card's printed preference (the icon on the left is preferred). The rulebook does not say what happens if neither first space is free (ruled in A-002: if neither first space is free, take the first empty space of the preferred type, else the first empty space of the other type).
Either way, give the rival the points, resources and life traces earned.

**Telescope (SOLO-RIVAL-08).** Mark the signals shown: a signal in the sector of Earth, and signals taken from the card row (use the decision arrow to decide leftmost or rightmost). If the rival has a telescope (pink) tech, it discards it and marks one extra card-row signal. After the rival finishes, replace the used card-row cards from the deck. When a signal could go in several sectors, the rival chooses in this order, ties going to the bigger sector: (1) a sector it would win, (2) a sector where the signal would score points for the second marker, (3) the sector where it has the most markers. A Telescope action is always possible.

**Species discovery check (SOLO-RIVAL-09).** Some cards start with "If the 1st (or 2nd) alien is discovered, replace this card with the corresponding alien card and resolve it." If that species is discovered, remove this card from the game, replace it with that species' card and resolve it; if not, skip to the next action.

**Passing (SOLO-RIVAL-10).** With no cards in the action deck the rival passes: remove the top card of the end-of-round stack (the rival advances 1 on the progress track); if the rival was first to pass, rotate the solar system.

**Life traces (SOLO-RIVAL-11).** When the rival earns a life trace, for each species look at that trace's column and mark the lowest free space, ignoring the overflow space unless the rest are full. With a wild trace, consider all columns; if the lowest spaces tie, use the decision arrow.

## Symbols on the cards

- Arrow on top: decision arrow, direction as drawn.
- "6 publicity", rotate disc, rainbow tech: pay 6 publicity, rotate the solar system, research any tech.
- Orange launch hex plus a publicity number: launch.
- Number with a probe-move arrow plus planets: moves and the planets to try in order.
- Probe-tech (orange) tile with a red cross, then moon: discard a probe tech to land on a moon.
- Green satellite hex: orbiter. Brown rover hex: lander. The one on the left, separated by a bracket, is preferred.
- Pink telescope hex, grey signal with a globe: a signal in the sector of Earth. Grey signal with a card: a card-row signal. Plus a pink tech with a red cross: discard a telescope tech for an extra card-row signal.
- Blue computer hex plus a blue tech with a red cross, then 3 VP and an orange arrow: analyze, with the computer-tech discard.
- Orange arrow with a 1: advance 1 on the progress track.


## The 19 cards

Order is top action first. Direction is the decision arrow.

### S.1 (basic, arrow left)

1. Analyze (no card benefit), then discard a computer tech for 3 VP and 1 progress

2. Launch a probe, gain 1 publicity

3. Pay 6 publicity, rotate the solar system and research a tech

4. Move the probe from Earth with 3 moves, planets in order: Saturn, Mars, Jupiter, Venus; first try to land on a moon by discarding a probe tech; otherwise tie preference: orbiter first, then lander

### S.2 (basic, arrow right)

1. Analyze (no card benefit), then discard a computer tech for 3 VP and 1 progress

2. Pay 6 publicity, rotate the solar system and research a tech

3. Telescope: 1 signal in the sector of Earth, 2 card-row signals; plus 1 extra card-row signal by discarding a telescope tech

### S.3 (basic, arrow left)

1. If the 1st alien species is discovered, replace this card with that species' card and resolve it

2. Pay 6 publicity, rotate the solar system and research a tech

3. Telescope: 1 signal in the sector of Earth, 2 card-row signals; plus 1 extra card-row signal by discarding a telescope tech

### S.4 (basic, arrow right)

1. If the 2nd alien species is discovered, replace this card with that species' card and resolve it

2. Move the probe from Earth with 3 moves, planets in order: Jupiter, Mars, Saturn, Venus; first try to land on a moon by discarding a probe tech; otherwise tie preference: orbiter first, then lander

3. No publicity cost, rotate the solar system and research a tech, advance 1 on the progress track

### S.5 (advanced, arrow left)

1. Analyze (card benefit: +3 VP), then discard a computer tech for 3 VP and 1 progress

2. Pay 6 publicity, rotate the solar system and research a tech, advance 1 on the progress track

3. Telescope: 2 signals in the sector of Earth, 1 card-row signal; plus 1 extra card-row signal by discarding a telescope tech

### S.6 (advanced, arrow left)

1. Pay 6 publicity, rotate the solar system and research a tech, advance 1 on the progress track

2. Launch a probe, gain 1 publicity, advance 1 on the progress track

3. Telescope: 2 signals in the sector of Earth, 1 card-row signal; plus 1 extra card-row signal by discarding a telescope tech

### S.7 (advanced, arrow right)

1. Pay 6 publicity, rotate the solar system and research a tech, advance 1 on the progress track

2. Move the probe from Earth with 4 moves, planets in order: Neptune, Saturn, Mercury, Venus; first try to land on a moon by discarding a probe tech; otherwise tie preference: lander first, then orbiter

3. Telescope: 2 signals in the sector of Earth, 1 card-row signal; plus 1 extra card-row signal by discarding a telescope tech

### S.8 (advanced, arrow left)

1. Analyze (card benefit: +3 VP), then discard a computer tech for 3 VP and 1 progress

2. Move the probe from Earth with 4 moves, planets in order: Uranus, Jupiter, Mercury, Venus; first try to land on a moon by discarding a probe tech; otherwise tie preference: lander first, then orbiter

3. Telescope: 2 signals in the sector of Earth, 1 card-row signal; plus 1 extra card-row signal by discarding a telescope tech

### S.9 (advanced, arrow right)

1. Analyze (card benefit: +3 VP), then discard a computer tech for 3 VP and 1 progress

2. Launch a probe, gain 1 publicity, advance 1 on the progress track

3. Move the probe from Earth with 4 moves, planets in order: Neptune, Uranus, Mercury, Venus; first try to land on a moon by discarding a probe tech; otherwise tie preference: orbiter first, then lander

### S.10 (advanced, arrow right)

1. Analyze (card benefit: +3 VP), then discard a computer tech for 3 VP and 1 progress

2. Launch a probe, gain 1 publicity, advance 1 on the progress track

3. Telescope: 2 signals in the sector of Earth, 1 card-row signal; plus 1 extra card-row signal by discarding a telescope tech

### S.11 (advanced, arrow right)

1. Pay 6 publicity, rotate the solar system and research a tech, advance 1 on the progress track

2. Analyze (card benefit: +3 VP), then discard a computer tech for 3 VP and 1 progress

3. Telescope: 2 signals in the sector of Earth, 1 card-row signal; plus 1 extra card-row signal by discarding a telescope tech

### S.12 (advanced, arrow left)

1. Pay 6 publicity, rotate the solar system and research a tech, advance 1 on the progress track

2. Launch a probe, gain 1 publicity, advance 1 on the progress track

3. Move the probe from Earth with 4 moves, planets in order: Mercury, Saturn, Jupiter, Venus; first try to land on a moon by discarding a probe tech; otherwise tie preference: lander first, then orbiter

### S.13 (advanced, arrow left)

1. Move the probe from Earth with 4 moves, planets in order: Neptune, Uranus, Mars, Venus; first try to land on a moon by discarding a probe tech; otherwise tie preference: lander first, then orbiter

2. Analyze (card benefit: +3 VP), then discard a computer tech for 3 VP and 1 progress

3. Telescope: 2 signals in the sector of Earth, 1 card-row signal; plus 1 extra card-row signal by discarding a telescope tech

### S.14 (advanced, arrow right)

1. Launch a probe, gain 1 publicity, advance 1 on the progress track

2. Pay 6 publicity, rotate the solar system and research a tech, advance 1 on the progress track

3. Telescope: 2 signals in the sector of Earth, 1 card-row signal; plus 1 extra card-row signal by discarding a telescope tech

### S.15 (species, mascamites, arrow right)

1. Launch a probe, gain 1 publicity

2. Move the probe from Earth: Saturn with 4 moves, then Jupiter with 5 moves; first try to land on a moon by discarding a probe tech; otherwise tie preference: lander only

3. Take a random Mascamite sample from the planet the rival targeted (it is taken together with the landing of action 2) and place it face up on this species board (ignore its reward).

### S.16 (species, anomalies, arrow left)

1. If the rival is not winning the next anomaly, they mark a trace of that color for this species and gain 3 VP.

2. No publicity cost, rotate the solar system and research a tech, advance 1 on the progress track

### S.17 (species, oumuamua, arrow left)

1. Move the probe from Earth to Oumuamua with 4 moves; place it as: lander first, then orbiter

2. Telescope: 1 signal in the sector of Earth, 1 card-row signal, 1 signal in the sector of Oumuamua; plus 1 extra card-row signal by discarding a telescope tech

### S.18 (species, centaurians, arrow right)

1. If the rival still has a Centaurian marker in their reserve and none on the scoring track, place one "+15" marker ahead of their current score. Then advance 1 on the progress track.

2. Telescope: 1 signal in the sector of Earth, 2 card-row signals; plus 1 extra card-row signal by discarding a telescope tech

### S.19 (species, exertians, arrow right)

1. Count the number of the rival's played Exertian cards and the rival's traces on this species board. If the total is less than 5, the rival secretly plays an Exertian card.

2. Telescope: 1 signal in the sector of Earth, 2 card-row signals; plus 1 extra card-row signal by discarding a telescope tech


## Differences from the repo's rival card data

- Every Analyze: the computer-tech discard (3 VP and 1 progress) is missing.
- Every Probe: the moon landing with a probe-tech discard and the first-space check are missing; only the tie preference is present.
- Every Telescope: the extra card-row signal for discarding a telescope tech is missing.

- S.7: Planets: the card shows Neptune, Saturn, Mercury, Venus. The repo lists Uranus, Saturn, Mercury, Venus.

- S.8: Planets: the card shows Uranus, Jupiter, Mercury, Venus. The repo lists Neptune, Jupiter, Mercury, Venus.

- S.9: Planet order: the card shows Neptune, Uranus, Mercury, Venus. The repo lists Uranus, Neptune, Mercury, Venus.

- S.19: Telescope: the card shows 1 Earth signal and 2 card-row signals. The repo uses mode EARTH, which is 2 Earth and 1 card-row signal on the other cards.
