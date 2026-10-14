# Card verification tracker

A web page where each card is checked by hand against a physical copy. Published as a claude.ai artifact: https://claude.ai/artifact/CDLZxgKryNB3hovoH4WoWA (private to the owner).

## Files

- `extract_cards.py`: extracts card data from a clone of the Ender-Wiggin2019/seti repo: `python extract_cards.py <repo>/packages/common/src cards.json`. `cards-extracted.json` is the current output.
- `prep_art.py`: stages the card art files (sprite sheets, expansion card images, organization images, a reduced rival action sheet) for upload as artifact assets.
- `art-meta.json`, `art-urls.json`: sheet sizes, and the stored asset url of each staged file in the artifact. `art-urls.json` is specific to the published artifact; if the artifact is recreated, upload again and regenerate it.
- `tracker-template.html`: the page source.
- `build_tracker.py`: builds the page: `python build_tracker.py cards-extracted.json art-meta.json art-urls.json tracker-template.html out.html`.

## Data and art

329 items in 10 groups: base main deck (138), base alien species cards (55), base solo rival action cards (19), expansion new main-deck cards (42), the two "SE EN" cards (2), Glyphids and Amoeba cards (20), Arkhos exploration (9) and security (12) cards, organizations (11), quick start cards (21).

287 items have a card image. The base and alien cards are cropped from the repo's sprite sheets by row and column, the 42 expansion cards and 11 organizations are single images, and the 19 rival action cards are cropped from the owner's rival sheet (cards S.1 to S.19 in reading order, 5 columns by 4 rows; the numbers are printed on the cards). The quick start cards and all Arkhos cards have no image in the repo.

## Stored checks

Checks are stored in the artifact's database, collection `verification`, one document per card, key `<group>:<id>`: `{status: confirmed | difference | unchecked, note, at, by}`. Claude reads them with the ArtifactData tool. Once a card is confirmed, its repo data can be treated as the verified source for the engine's card definitions.

Known limits of the repo data: the Arkhos exploration cards have no effect data, and the Arkhos security cards carry only a generic text per trace color.
