# Rules without a test: the data, layout and UI rules

Written 2026-10-19 for the 1.0 checklist (section A and the owner's decision list). These are the rules that `tools/engine/rule_coverage.py` reports as having no test and that describe tables, pictures or components instead of behaviour. CLAUDE.md hard rule 2 says every rule ID has a test. The proposal below keeps that rule for all but a few rules that only describe a picture, a component list or a UI element.

- **Write a test:** 20 rules (data tests that compare the engine's tables with the spec, count tests, and a few setup behaviours).
- **Already covered, add the ID:** 16 rules (an existing test checks them, the ID is not named).
- **Exempt:** 11 rules (needs the owner's approval, and a decision-log entry since it changes how hard rule 2 is applied).

| Rule | What it says | Action | What happens |
|---|---|---|---|
| BOARD-01 | Discs and Sun: rings, spaces, adjacency, comets, asteroids, planets, Earth | Write a data or behaviour test | Data test: the cell tables in `solar.py` against `board-solar-system.md` (spaces per ring, positions of Earth, planets, comets, asteroids). |
| BOARD-02 | Legal starting layouts of discs and sector boards | Write a data or behaviour test | Behaviour test: for many seeds, setup gives eight sectors with one star each and a valid disc layout. |
| BOARD-03 | The 8 stars, their colors (each color twice), slot sizes | Write a data or behaviour test | Data test: names, colors (each twice), capacities against the spec table. |
| BOARD-04 | Publicity icons on spaces, visit rewards of planets and comets | Write a data or behaviour test | Data test of the visit-reward table; the publicity-on-visit behaviour is already tested (MOVE-05). |
| BOARD-05 | Planetary board: orbit, lander, first-lander, moon rewards | Write a data or behaviour test | Data test of the planet table against the spec. |
| BOARD-06 | Tech board: positions of 12 stacks and the rotation counter | Exempt (needs the owner's approval) | Picture layout only. The stacks and the counter are tested under TECH-xx and ROTATE-xx. |
| BOARD-07 | Publicity track 0 to 10, score track, milestone spaces 20, 25, 30, 50, 70 | Already covered: add the ID to the test | Cite in the milestone tests (the constants are checked there) and the publicity cap test. |
| BOARD-08 | Player board layout (tech slots, computer, data pool) | Exempt (needs the owner's approval) | Picture layout. Each element is tested under its own rule (RES-01, TECH-2x, ANALYZE-xx). |
| BOARD-21 | Data slot sizes 4 to 6 per star | Write a data or behaviour test | Data test with BOARD-03. |
| BOARD-22 | Each contributing player gains 1 publicity; second position scores 2 | Already covered: add the ID to the test | Already tested as SECTOR-03 and SECTOR-12: add the ID to those tests. |
| BOARD-23 | Winner rewards of each sector (first and later wins) | Write a data or behaviour test | Data test of the winner-reward table. |
| BOARD-30 | Orbit rewards; the first orbiter scores 3 | Already covered: add the ID to the test | Already tested under ORBIT-01 to 04: add the ID. |
| BOARD-31 | Lander rewards; first-lander data; Mars has two | Already covered: add the ID to the test | Already tested under LAND-03, LAND-04: add the ID. |
| BOARD-32 | Moons: one lander space each, own reward | Already covered: add the ID to the test | Already tested under LAND-05: add the ID. |
| BOARD-50 | 12 tech stacks in 3 rows, 4 tiles each, glyphs | Write a data or behaviour test | Data test: 12 stacks, 4 tiles, categories and glyphs. |
| BOARD-51 | Bonuses on the four tiles of a stack | Write a data or behaviour test | Data test of the tile bonus table (owner already verified the tile data). |
| BOARD-52 | Extra immediate bonuses of two stacks | Already covered: add the ID to the test | Already tested as TECH-PT01 and TECH-TT01: add the ID. |
| BOARD-53 | Rotation counter: ring 1, rings 1+2, rings 1+2+3 | Write a data or behaviour test | Behaviour test: three rotations advance the counter and the discs that turn. |
| BOARD-54 | Nonplayer markers by player count | Write a data or behaviour test | Behaviour test: setup gives 0, 1 and 2 nonplayer markers for 4, 3 and 1 to 2 players. |
| BOARD-60 | Publicity track: start on 4, research and buy boxes | Already covered: add the ID to the test | Start and cap are tested now (SETUP-34, RES-02); buy and research at any publicity at or above the cost: add the ID to those tests. |
| BOARD-61 | Score track and the 100/200 token | Already covered: add the ID to the test | Add the ID to the milestone tests (MILE-04 test). |
| BOARD-70 | Data pool of 6; place first, then take the new data | Already covered: add the ID to the test | Tested under RES-01 and SECTOR-02: add the ID. |
| BOARD-72 | Computer tech slots behind spaces 1, 3, 5, 6 | Already covered: add the ID to the test | Tested under TECH-20 and TECH-21: add the ID. |
| BOARD-73 | Analyze: 1 energy, full top row, clear, blue trace | Already covered: add the ID to the test | Tested under ANALYZE-01 to 03 and ANALYZE-02 (now): add the ID. |
| BOARD-74 | Four probe and four telescope tech slots | Already covered: add the ID to the test | Tested under TECH rules: add the ID. |
| BOARD-75 | Costs printed on the player board edge (repeat other rules) | Exempt (needs the owner's approval) | A repeat of LAUNCH-01, SCAN-01 and TECHACT-01; nothing to test. |
| ALIEN-DATA-01 | Species boards: spaces, colors, rewards, costs | Exempt (needs the owner's approval) | Data transcribed from the pictures and reviewed by the owner; behaviour is tested per species. |
| ALIEN-DATA-02 | Species cards, tokens and their faces | Exempt (needs the owner's approval) | Card data was confirmed by the owner (card review page); each card has a smoke test. |
| ALIEN-DATA-03 | Mascamite samples, the 'Oumuamua tile, Exertian cards | Write a data or behaviour test | Data test: 7 samples and their rewards, the Exertian card table (danger and points). |
| ALIEN-DATA-11 | Spaces with a cost; the top capsule can be marked repeatedly | Write a data or behaviour test | Behaviour test for each cost type (Centaurian data, 'Oumuamua exofossils) and the repeated top capsule. |
| ALIEN-DATA-12 | The alien card icon: draw or take the face-up card | Write a data or behaviour test | Behaviour test: an alien card gain offers the deck and the face-up card. |
| ALIEN-DATA-13 | Overflow and discovery spaces are on the planetary board | Already covered: add the ID to the test | Tested under LIFE-01, LIFE-03 and BOARD-40: add the ID. |
| SOLO-DATA-01 | Rival boards, difficulty 1 to 5 | Write a data or behaviour test | Data test: objective stack, start space, progress track per difficulty. |
| SOLO-DATA-02 | The 24 objective tiles | Exempt (needs the owner's approval) | Tile tasks come from pictures; the owner has not yet verified them. Needs the owner's check, then no further test. |
| SOLO-DATA-11 | Progress track: ring of 12, order of colors and glyphs | Write a data or behaviour test | Data test of the track order. |
| SOLO-DATA-13 | Objective table: 1 to 4 objectives per round, 5 VP each at the end | Already covered: add the ID to the test | Tested in the solo tests: add the ID. |
| SOLO-DATA-20 | 4 level I, 11 level II, 9 level III tiles | Write a data or behaviour test | Count test. |
| SOLO-DATA-30 | Gold tiles: three score slots | Already covered: add the ID to the test | Tested under END-10 to END-17: add the ID. |
| SETUP-01 | The three parts of the main board | Exempt (needs the owner's approval) | A description of components. |
| SETUP-02 | Pieces of each player color | Exempt (needs the owner's approval) | A description of components (unlimited markers are tested under RES rules). |
| SETUP-03 | General pieces: 48 tiles, 138 cards, 70 data ... | Write a data or behaviour test | Count test: 48 tiles, 4 gold tiles, 138 cards, supply sizes. |
| EXP-02 | Expansion components: 11 organizations, 21 quick start, 42 cards ... | Write a data or behaviour test | Count test. |
| EXP-04 | Expansion cards carry the expansion icon | Exempt (needs the owner's approval) | UI only; the rule says nothing to implement. |
| ALIEN-UI-01 | Score track shows message tiles and Exertian milestone tiles | Exempt (needs the owner's approval) | UI only (not a rule). |
| ALIEN-MASC-06 | Collected samples stay face down for other players | Already covered: add the ID to the test | The projection test already hides them; add the ID (CLAUDE.md rule 6). |
| TECH-01 | 12 technologies, 4 tiles each; one per technology | Write a data or behaviour test | Count test plus: a player cannot take the same technology twice. |
| TECH-02 | Immediate bonus on each tile | Exempt (needs the owner's approval) | Tile data verified by the owner; the bonuses are tested one by one (TECH-PTxx, TECH-TTxx, TECH-CTxx). |

## The behaviour rules

Written as tests on 2026-10-19 (`tests/test_rule_gaps.py`, `tests/test_rule_gaps_2.py`, `tests/test_data_rules.py`, and rule IDs added to the tests that already checked them): about 110 rules. Coverage went from 248 to 403 of 418 rules with a test.

Still without a test, besides the exempt rules above:

| Rule | What it says | Why it is not written yet |
|---|---|---|
| CARD-41 | "signal in a sector": the card names where | Needs a card with a named sector in the test setup |
| FAQ-32 | One action can mark both an objective task and a triggerable mission circle (solo) | Needs a solo state with both set up |
| FAQ-55 | The rival's 'Oumuamua card: move to 'Oumuamua within 4 moves, then land or orbit | Needs a rival state with 'Oumuamua discovered and a probe in range |
| EXP-PROMO-01 | The promo card "Space Agencies" | Not implemented; the owner decided on 2026-10-19 to leave it as it is |
