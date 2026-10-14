# Asset inventory

Source repo: https://github.com/Ender-Wiggin2019/seti (pnpm/Turborepo, TypeScript, Next.js web package). Surveyed 2026-10-12. Sizes are approximate.

## Packages

| Package | Contents | Useful to us |
|---|---|---|
| `packages/cards` | `assets/images` (15 MB): card sprite sheets, card templates, mission containers, alien and alien-filter art, icon sheets (`seti-icons*.webp`), `CardRender.tsx` | Card art and the renderer |
| `packages/common` | TypeScript rules helpers (`src/rules`), card data (`src/data`), constants (`src/constant`), protocol types, locales, tests | **Cross-check source only**, not authoritative |
| `packages/web` | Next.js site, `public` (26 MB): the same assets, corporation art, icons, locales, posts | Mostly duplicates `cards` |
| `packages/client` | `public` with the same seti-assets | Duplicate |

## Image assets (in `packages/cards/assets/images`)

- `cards/cards-1.webp`, `cards/cards-2.webp`: base card sprite sheets, addressed by row and column in the card data.
- `cards/space-agency/`: 42 space-agency card images.
- `cards/card-template.webp`, `mission-*.webp`, `end-game-container.webp`, `quick-mission-reward.webp`: card parts.
- `aliens/`: 7 alien images (amoeba, anomalies, centaurians, exertians, glyphids, mascamites, oumuamua). `alien-filter/`: 8 filter images, including `ark`.
- `seti-icons.webp`, `seti-icons-2.webp`, `seti-icons-3.webp`, `move-icon.webp`, `prelude-back.webp`: icon sheets.

## Data (TypeScript, `packages/common/src/data`)

| File | Entries |
|---|---|
| `baseCards.ts` | 140 |
| `alienCards.ts` | 55 |
| `spaceAgencyCards.ts` | 42 |
| `preludeCards.ts` | 23 |
| `rivalActionCards.ts` | 19 (solo mode) |
| `organizations.ts` | 13 |
| `arkhosCards.ts`, `fanMadeCorps.ts`, `spaceAgencyAliens.ts`, `flavorTexts.ts`, `faq/` | misc |

Rules helpers in `packages/common/src/rules`: actions, computer, movement, planet, sector, solar system and wheels, tech, free actions, hand limit. Constants include `solo.ts` (rival board configs, difficulties 1 to 5) and `sectorSetup.ts`. These are a fan's interpretation. We read them to find questions, and we do not copy rules from them.

## Not present

Board, solar-system, tech-board and token art are not in the repo. See [asset-gaps.md](asset-gaps.md).

## Import rule

Nothing has been copied into this project yet. When assets are imported they go into `packages/assets/` with a provenance manifest (`PROVENANCE.md`: source path, upstream commit, date imported, license status).
