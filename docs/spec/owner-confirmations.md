# Owner confirmations from physical copies

Facts the owner checked against physical components. Each one is a source for the spec (rulebook plus physical card), and overrides the repo's card data (Ender-Wiggin2019/seti) where they differ.

## SOLO-ANALYZE (rival action cards, ANALYZE action)

- Physical card S.1, analyze row: if the rival has a blue (computer) tech, it discards one and scores 3 VP and advances 1 on the progress track. The owner confirmed this on 2026-10-12.
- Rulebook, solo game, Analyze: "If the rival has a computer tech, they discard it and gain 3 points and 1 progress. (Even if the rival has multiple computer techs, they can only discard one.)" This comes after the rival clears its computer, takes the benefit shown on the card and the reward on its player board, and moves its remaining data pool tokens into the computer.
- Repo data: `analyze()` on S.1 carries no effects, and `analyze([VP_3])` on later cards means an extra 3 VP printed on the card. The computer-tech discard is not in the repo's rival card data, and the repo has no solo implementation of it. The engine must implement it as part of every Analyze action.

## SOLO-PROBE (rival action cards, probe placement after movement)

- Physical card S.1, probe row, confirmed by the owner on 2026-10-12. After the rival's probe reaches a planet:
  1. If the planet has a moon with an available space and the rival has an orange (probe) tech, it discards that tech and lands on the moon. If several moons are available it uses the decision arrow (leftmost or rightmost).
  2. Otherwise it tries the first orbiter space, or the first lander space, of the planet.
  3. If both first spaces are available, or neither is, it uses the preference printed on the card. On S.1 the preference is orbiter.
- Rulebook, solo game, probe action: "If the planet has a moon with an available space, the rival will first try to discard one of their probe technologies to land on it. If multiple moons are available, the rival chooses the leftmost or rightmost, depending on the decision arrow. If the rival does not land on a moon, the rival tries to take the first orbiter space or the first lander space on the planet. If both first spaces are available, or if neither is, the rival defers to the action card instead."
- Repo data: `probe({ movement, planets, probePlacement })` keeps only the card's own parameters. `probePlacement: ORBITER` matches the S.1 preference, but it is only step 3. The moon landing with a tech discard (step 1) and the first-space check (step 2) are not in the repo data and the repo has no solo implementation. The engine must implement all three steps for every probe action.

## Rival action cards, full rewrite (2026-10-12)

The repo's solo data was found to be incomplete and partly wrong, so all 19 rival action cards were transcribed from the card art and the base rulebook (pages 23 to 26): see `docs/spec/solo-rival-cards.md` (rules and card list), `docs/spec/data/rival-action-cards.json` (data) and the "Solo rival action cards" group in the card tracker. Status: waiting for the owner to check each card in the tracker. Until a card is confirmed there, treat its entry as a draft.

## Check pages confirmed, 2026-10-13

The owner confirmed every row of the alien species, solo and scoring, and card definitions check pages (snapshots in `data/board-check-alien.json`, `data/board-check-solo-scoring.json`, `data/board-check-card-defs.json`), with these notes:

- Objective tiles: the strip with a check does not mean "mark a signal" but "**win a sector**" (the grey one: a sector of any color; a colored one: a sector of that color). Applies to L1 "land / win a sector", the L2 pairs of colors, L3 black, and L3 "telescope tech, win a sector of any color". The data was corrected (`tools/board/solo_scoring_data.py`, `data/objectives.json`).
- The green "2 VP" tab is the 2-point tile on top of each tech stack (first taker scores 2). The gray boxes are expansion components.
- The 81 re-checked cards (53 base, 13 alien, 15 Exertian) are confirmed against the card images, with the Exertian danger and end-of-game notes as the rule for those cards.

## Anomaly token placement, 2026-10-14

The owner re-checked ALIEN-ANO-01 against the rulebook: one token in Earth's sector, the others 3 sectors either side. The spec text was right and is unchanged. Placement (`anomalies_placed`) and each resolution (`anomaly`) are now written to the log.

## Scan steps are resolved in any order, 2026-10-22

This replaces the ruling of 2026-10-17 below. The rulebook (p.12) lets the player resolve the steps of a scan in any order (SCAN-01), and the site now does: every step that is left can be done at any time, one at a time, and the player finishes the scan when they want to once the two steps that are not optional are done. For example, with the telescope tech of TECH-TT04 the player can spend 1 energy to launch a probe, or gain 1 free movement, before the signal in Earth's sector; or discard a card of the row (SCAN-03) for a signal before it. `techs.scan_moves` offers the moves of all the steps that are left, and `scan_done` once the signal in Earth's sector and the card of the row are done (or cannot be done). A step that cannot be done now (no publicity, no energy, no matching card) is not offered but stays in the list: a reward earlier in the scan can make it possible. The move `scan_skip` is not offered any more (leaving a step undone is finishing the scan); the engine still accepts it where the old rule accepted it, so that games played from left to right replay.

## Scan steps are resolved from left to right, 2026-10-17 (replaced on 2026-10-22, see above)

The rulebook (p.12) lets the player resolve the steps of a scan in any order (SCAN-01). The owner ruled that the site resolves them from left to right, one at a time:
1. a signal in Earth's sector (or in a sector next to it with the telescope tech of TECH-TT01);
2. discard a card of the row for a signal in a sector of its color (SCAN-03);
3. (expansion, EXP-SIG-02) discard signal tokens for more cards of the row;
4. with the telescope techs, in the order of the player board: spend 1 publicity for a signal in Mercury's sector (TECH-TT03), discard a card of the hand for a signal (TECH-TT02), spend 1 energy to launch a probe, or gain 1 movement for free (TECH-TT04).
Steps 1 and 2 cannot be skipped; the others can. A step that cannot be done (no publicity, no energy, no matching card) is passed over. The engine offers only the moves of the current step (`techs.scan_moves`), and the context bar says which step it is.

## Futurespan Institute: the card of the free action, 2026-10-18

Moving the Futurespan token 3 spaces farther (EXP-ORG-12) gains 1 card that the player takes from the card row or from the deck, like any card gained. This replaces the earlier reading (A-036) of a random card from the deck.

## Glyphids: the top row of the board takes any number of markers, 2026-10-18

The three top spaces of the Glyphids board (EXP-GLY-04) are replenished at once, so they take any number of markers, like the top capsule of the base species boards (`repeat` in `expansion-glyphids.json`); each marker takes the new token. The lower spaces take one marker.

## Servicing Mission (SA.5) and SA.38: "then" comes after the movement, 2026-10-23 (EXP-SA5-01)

"Gain 1 data and 1 movement. Then, if you have a probe on a space adjacent to Earth, return this card to your hand." The check comes **after** the player had the chance to
use the movement that the card gave (a free action may interrupt a card, FREE-00). The engine asks the player (the decision `hold`, the move `hold_done`) when the condition
is not true yet and the player has a movement and a probe; a probe moved with that movement counts. The same order holds for SA.38 (a probe sharing a space, 3 VP).
Reported by a player (a probe moved next to Earth with the movement and the card was not returned); decided by the owner.

## NASA Exoplanet Archive (SA.35): the data of the computer, 2026-10-23 (EXP-SA35-01)

"A total of at least 12 data in your computer and data pool": the computer is every space (ANALYZE-02), so the data on the lower spaces of the computer techs count with the top
row and the data pool. (The engine counted the top row and the pool only; a player with 13 could not complete the mission.)
