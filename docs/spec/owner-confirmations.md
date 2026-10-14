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

The owner corrected ALIEN-ANO-01: the tokens go opposite Earth and 2 sectors clockwise and counter-clockwise of Earth (earlier text said Earth's sector and 3 either side). The rule sheet PDF is not in the repo (`docs/rules/` is absent), so this was not re-checked against the sheet; the owner should confirm against it. Placement and each resolution are logged.
