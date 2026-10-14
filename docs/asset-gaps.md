# Asset gaps

Updated 2026-10-12 after the owner supplied images in `assets/`. See [../assets/MANIFEST.md](../assets/MANIFEST.md) for the label of every file, [asset-removals.md](asset-removals.md) for what was deleted, and [asset-inventory.md](asset-inventory.md) for the Ender-Wiggin2019/seti repo survey.

## What happened to the 198 supplied files

| Result | Count |
|---|---|
| Renamed and labeled | 180 (plus 2 files added later: Arkhos board and card back) |
| Deleted: non-English (German, Russian) | 10 |
| Deleted: duplicates (identical or same board re-encoded) | 2 |
| Moved to `assets/_duplicates-review/` for the owner to decide | 6 |

The six in review are the low-resolution (436x608) card backs of the same artwork as the 747x1040 scans. They are not byte-copies: the small ones are a cleaner digital version with a different color grade. I kept them out of the main folder but did not delete them. Say "delete" or "keep" and I will act.

## Newly found: the board and tokens are no longer missing

The earlier gap list is now mostly covered: main board, player boards, solar system discs, sector boards, tech tiles, objective tiles, gold scoring tiles, alien boards, resource tokens, and the solo rival boards are all present.

## Still missing or unclear

| # | Item | Why it matters | Placeholder plan |
|---|---|---|---|
| 1 | **Card art and data come from the GitHub repo** (owner decision, 2026-10-12). The repo's base card data has all 138 ids (1 to 138, including #130). The English card sheets in `assets/` (`cards-main-deck-en-sheet-*`, `cards-alien-*-en-sheet`) are now redundant. | Resolves the earlier worry that the English deck was short. The German overflow sheet held #130, which the repo has. | Keep the sheets for now as a visual cross-check source; owner decides whether to delete them. |
| 2 | **Expansion (Space Agencies) components**: 11 organizations, 21 quick start cards, 3 long-term objective tiles, 3 Xenolab tiles, 1 Futurespan token, 10 signal tokens, 4 rival action cards, 42 new main-deck cards | Needed for games with the expansion | Not in `assets/`. The repo has `spaceAgencyCards.ts` (42 cards), `organizations.ts` (13), `rivalActionCards.ts` (19, base solo) and `spaceAgencyAliens.ts`; to be checked against the expansion rulebook. |
| 3 | **Expansion alien species**: Amoeba board present (no cards or organelle tokens in `assets/`); Glyphids board and 3 component variants present (no cards, glyph tokens or strip tiles); Arkhos board and card back present (no exploration or security cards) | Same | Cards from the repo (`alienCards.ts`, `arkhosCards.ts`); tokens as SVG placeholders |
| 4 | **Player pieces**: figures, markers, publicity and score counters, 100/200 tokens, data tokens, rotation tokens | Board pieces | SVG placeholders in player colors. `marker-plus15-*` may be the score marker. |
| 5 | **Alien species components** for the five base species: Exertian milestone tiles, Centaurian message tiles, Anomaly tokens, Oumuamua exofossil tokens (one found), Mascamite samples (all 7 faces and the back found) | Alien play | Partly present. Several tokens are labeled `probable` in the manifest. |
| 6 | **Unidentified assets** (labeled `unidentified` in the manifest): `icon-container-*`, `icon-magenta-signal-card`, `tab-*` (5 notched tabs), `agency-cards-observatory-4-colors-sheet`, `card-back-sunny-radio-telescope` | I could not tell what these are from the art alone | Owner to identify, or they stay unused |
| 7 | **Not SETI**: `logo-widgets-workshop-NOT-SETI` (the TTS mod author's logo), `tts-table-alien-species-layout-NOT-SETI` (a Tabletop Simulator table), `skybox-milky-way` (TTS background) | Should not ship | Recommend deleting the first two. The skybox could be a site background if its license is clear. |

## Quality notes

- Probable-labeled tech tiles: the category (probe, telescope, computer) is inferred from color and icons, and the corner glyphs are named `dot`, `link`, `branch`, `cross` by shape. They should be checked against the rulebook when the spec is written.
- All card text is baked into the images. The engine cannot read it, so card data comes from the repo's TypeScript data, to be verified against the card images (see the open question in the status message).
- The main deck, alien cards and income cards have no official art separate from the text, so the website will show the whole card image.

## Licensing

- The repo `Ender-Wiggin2019/seti` has no LICENSE file, and the owner's permission rests on the owner's statement.
- The supplied `assets/` come from Steam Workshop (Tabletop Simulator) content of unknown authorship. Their license and permission status are not recorded. The owner should record the source and permission for these before any public launch (see [../LEGAL.md](../LEGAL.md)).

## Updates

- 2026-10-12: the owner identified `alien-board-glyphids*` (renamed from the green fan-made board and its three track variants) and added `alien-board-arkhos` and `card-back-alien-arkhos`. The AI-generated watermark remains on `alien-board-glyphids.png`; re-source it if we want a clean image.
- 2026-10-12: searched for a clean copy of the Glyphids board and its variants (CGE, Asmodee, BoardGameGeek, print-and-play). None found online. The only image is a retail photo showing the three expansion alien boards together (Asmodee product gallery), which is not a usable scan. A clean copy needs a scan or export from a physical copy.
- 2026-10-12: expansion work is deprioritized (PLAN.md D22) until all expansion assets (items 2 and 3 above) have a source.

- 2026-10-12: correction to the earlier labels. `player-board-a/b/c/d` were mislabeled: they are the solo **rival boards** (renamed `rival-board-4-star`, `-5-star`, `-1-2-star`, `-3-star`), and `solo-rival-board-v1/2/3` are Tabletop Simulator mats (renamed `tts-rival-mat-v*`). **The human player board is not in `assets/`** (gap): its layout is read from the rulebook p.6 and p.14 pictures and the tech board; if you have a clean image of the player board, please add it.
- 2026-10-14: the game page now needs two pieces of art that are not in `assets/` (item 4 above). Both are drawn as SVG placeholders in `apps/web/src/components/BoardView.tsx`
  until the owner supplies them: (1) the **data token**, shown as a blue disc in every sector (a picture of the real blue data token, one file); (2) the **probe figure** of each
  player colour (green, red, purple, white), used for probes in space, for orbiters (with a ring) and for landers (with a base). A top-down or three-quarter picture of each
  coloured pawn is enough, with a transparent background. Found and now used: `texture-moon-disc.png` (the moon token that marks the disc to rotate next) and
  `tab-green-2vp-first-taker-tile.png` (the +2 tile on the tech stacks). `solar-rotation-token-white-disc.png` is not used.
- 2026-10-14 (later): the page now draws the player pieces itself (`apps/web/src/components/Pieces.tsx`), after the photographs on page 2 of the rulebook: the figure (a radio dish on a
  stem and a round base: probe, with a ring for an orbiter and a base line for a lander), the marker (a short cylinder with a dimple, also in blue for data and in grey for the
  neutral markers), the publicity counter (microphone-shaped) and the score counter (a crest with a globe in a laurel wreath), each in the four player colours. They replace the
  earlier placeholders; real pictures of the pieces would still be better if the owner has them. `skybox-milky-way.jpg` (listed above as a TTS background that should not ship) is used
  as the page background at the owner's request; `card-back-sunny-radio-telescope.png` (the back of the main deck) shows the piles of the coming rounds.
- 2026-10-14 (later still): the data token is drawn by `DataToken` in `apps/web/src/components/Pieces.tsx` (a blue glossy button with three bars of data). The curved slot of every star
  is found on the picture of the ring by `tools/web/build_assets.py` (`apps/web/src/generated/slots.json`): a slot is as long as the data of its star, so the tokens lie at equal steps
  along it from the counter-clockwise end. A marker takes the leftmost token's place and the token lifts off towards its owner's data pile (shown in the tracker).

- 2026-10-14: the symbols for credit, energy, a card of the display and a card of the deck (`apps/web/src/components/Icons.tsx`) are drawn placeholders, as are the tech names in `apps/web/src/lib/techs.ts` (the tiles show icons only, so the 12 short names are our own). If you have the printed symbols or official names, send them.

- 2026-10-14: more drawn placeholders for the log and the confirmations: the icons of publicity, data, alien card, exofossil and trace (`apps/web/src/components/Icons.tsx`). The icons of the main actions (launch, orbit, land, scan) are cut from the player aid, and the score icon is the globe of the scoring track. The places of the trace spaces on the five species boards (`apps/web/src/lib/speciesSpaces.ts`) were measured by eye on the pictures (the sample spaces of the Mascamites have no place yet and stay buttons); the overflow spaces are placed 190 px under the discovery spaces.

- 2026-10-14: the site icon (`apps/web/src/app/icon.png`, `apple-icon.png`, `favicon.ico`) is a circle cut from the SETI box art picture that the owner pointed to (the Open Graph image of the game's BoardGameGeek page, 1200 x 630): the word SETI and part of the orange dish. It is a fan-project use of CGE's artwork like the other pictures; replace it if CGE or the owner asks.

- 2026-10-14: the player board (`apps/web/src/components/PlayerBoard.tsx`) is drawn, as there is no picture of it among the assets: the six computer spaces, the four tech slots behind spaces 1, 3, 5 and 6, the probe and telescope techs and the data pool. The tech tiles on it are the printed fronts. A picture of the real board would replace the drawing.
- 2026-10-14: Mascamite sample tokens (face-down back and the 7 faces) are drawn placeholders on the board (a purple disc with an S) and in the Mascamite samples tab, until the art is in the asset repo (`apps/web/src/components/BoardView.tsx`).
