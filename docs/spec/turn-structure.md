# Turn and round structure

Source: base rulebook pp. 7, 18, 19, 21, 28.

## Game

- **GAME-01** (p.7) The game lasts 5 rounds.
- **GAME-02** (p.7) The player with the starting player marker takes the first turn of each round. Players take turns in clockwise order, skipping any player who has passed this round.
- **GAME-03** (p.7) After the fifth round, the final score is calculated and the player with the most points wins (see END-01).

## Turn

- **TURN-01** (p.7) On their turn a player takes exactly one main action from: launch a probe, orbit a planet, land on a planet or moon, scan nearby stars, analyze data, play a card for its effect, research a tech, pass for the round.
- **TURN-02** (p.7) Free actions may be taken at any time during the player's own turn: before, after, or during the main action. Free actions cannot be taken outside the player's own turn, including between turns (p.28).
- **TURN-03** (p.7) When a card is used it is used for only one of its benefits: if its effect is played as a main action it cannot also be discarded for its free action, and the reverse.
- **TURN-04** (p.7, p.18) The turn ends once the main action and any free actions are done. Completed sectors have been resolved right after the main action (TURN-05, A-005); then, in this order: resolve milestones (MILE-10), then any species discovery (ALIEN-01). Then it is the next player's turn.
- **TURN-05** (p.13, A-005) The sectors completed by a main action are resolved when that main action is finished (not at the end of the turn: the player still has their free actions afterwards, but none of them changes how these sectors are resolved), in any order the player chooses. Owner ruling, 2026-10-14: the engine asks the player which completed sector to resolve next (the last one is resolved without asking); the solo rival resolves the lowest-numbered first.

The rulebook gives the order of the end-of-turn steps in three places: sectors "when you finish your main action" (p.13), milestones "between turns, after the current player has finished playing free actions" (p.18), and discovery "after you finish your turn; if there are any milestones, resolve them before resolving the discovery" (p.20). The order above follows all three. Whether completed sectors are resolved before or after free actions the player still wants to take is open: A-005 (the rule on p.13 says "when you finish your main action", but a player can still take free actions afterwards).

## Passing

- **PASS-01** (p.19) Passing is a main action. A player who passes may take free actions on the turn in which they pass, and then resolves the following steps in order without taking further free actions.
- **PASS-02** (p.19) Step 1: discard down to 4 cards if the player has more than 4 in hand. (Alien cards in hand count as cards, except Exertian cards, which are not in hand: p.20, p.28.)
- **PASS-03** (p.19) Step 2: check whether to rotate the solar system. If the player is the first to pass this round, take the rotation reminder token (it sits on this round's stack of end-of-round cards), set it beside the stack, then rotate the solar system (ROTATE-01). In round 5 the player still rotates but discards the reminder token.
- **PASS-04** (p.19) Step 3: choose one card from this round's end-of-round cards and put it in hand; return the rest. The player who passes earlier has more cards to choose from. The final player to pass chooses one of the 2 remaining cards and discards the leftover card. (In round 5 there is no end-of-round card stack in use for choosing: the rulebook says rounds 1, 2, 3 and 4 only, see PASS-05.)
- **PASS-05** (p.5, p.19) End-of-round cards exist for rounds 1 to 4 only (4 stacks). In round 5 the passing player does steps 1 and 2 only.
- **PASS-06** (p.19) Optional: players may resolve their income at any time after passing, even before the round ends, to speed up the game (INCOME-04).

## Round end

- **ROUND-01** (p.7, p.19) The round ends when all players have passed (after the last player has resolved PASS-04).
- **ROUND-02** (p.19) Between rounds, in this order: (1) everyone gets income; (2) the starting player marker moves one space to the left, i.e. to the next player in clockwise order; (3) the rotation reminder token moves onto the stack of end-of-round cards for the next round.
- **ROUND-03** (p.19, p.21) After round 5 the game ends and final scoring happens (END-01). Income is not collected after round 5.

## Income

- **INCOME-01** (p.6) Tucking a card for income: tuck the card from hand under the player's starting income card. It permanently adds to income and the player immediately gains the resource printed in the bottom-right corner of the tucked card.
- **INCOME-02** (p.6, p.14) The "tuck a card for income" effect comes from: the setup step (SETUP-36), the income space of the player's computer (FREE-04), orbiting (ORBIT-05), and card or board effects that show the icon. When it occurs the player tucks a card from hand. What happens with an empty hand is not stated: A-013.
- **INCOME-03** (p.6, p.19) At the start of each round from round 2, each player gains: the resources printed on the right of their starting income card (3 credits, 2 energy and 1 random card), plus the resource of each card tucked under the starting income card.
- **INCOME-04** (p.19) A player may resolve income at any time after passing, even before the round ends. (Open: whether this allows free actions with the new resources after passing. PASS-01 says no further free actions are played after the pass steps. A-006.)
- **INCOME-05** (p.6, p.28) When tucking a card, the player gains the resource immediately. Cards used for income are removed from the hand.

## Resource and hand rules

- **RES-01** (p.14) A player's data pool holds at most 6 data. Data gained beyond this is discarded. Before gaining data that would overflow the pool, the player may place pool data into the computer (a free action, FREE-03, during their own turn) to make room (owner note, 2026-10-13). Owner ruling, 2026-10-14: this must be allowed: the engine asks (`data_overflow`) whenever a gain on the player's own turn would overflow a pool that can still be placed; the player places data one at a time or takes the gain and loses the extra.
- **RES-02** (p.28) A player with 10 publicity ignores effects that give more.
- **RES-03** (p.19) Hand size is only limited when passing (PASS-02).
- **RES-04** (p.19, A-026) Refilling the card row: when a card is drawn from the card row (a free action: 3 publicity or a trade), it is replaced immediately from the top of the deck, and only that card is replaced: a gap that a running scan has left stays until the scan is finished (SCAN-03). If the deck is empty, shuffle the discard pile to form a new deck.
- **RES-05** (p.19) Two draw effects exist: "draw a card from the card row or the top of the deck" (player's choice), and "draw a random card from the top of the deck" (not the card row).
- **RES-06** (p.18) Resource exchange (free action): 2 cards, 2 credits or 2 energy (two of the same kind) can be exchanged for 1 card, 1 credit or 1 energy. Two different resources cannot be combined (p.28). When the target is a card, the player draws it from the card row or the top of the deck. Alien cards in hand count as cards (p.28), except Exertian cards.
