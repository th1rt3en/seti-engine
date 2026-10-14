# Solar system board (confirmed by the owner, 2026-10-12)

Transcribed from the board images (`assets/solar-disc-*.png`, `assets/main-board-assembled.png`) and cross-checked against the repo's `sectorSetup.ts`: all 11 rows agree. The owner checked and confirmed all 15 items (5 rules and 10 wheel rows) in the board check page (`tools/board/`); the marks are in `data/board-check-solar-system.json`.

## Conventions

- Slot k (0 to 7) is the 45-degree wedge from k*45 to (k+1)*45 degrees, counted counter-clockwise from the 3 o'clock direction of the image as printed. Rings are numbered from the Sun outward, 1 to 4.
- **BOARD-10** (owner ruling A-007) One rotation step is 1/8 of a turn, counter-clockwise: the content of slot k moves to slot k+1.
- **BOARD-11** (owner ruling A-007, p.16) Rotating disc 1 turns disc 1. Rotating disc 2 turns disc 2 and disc 1. Rotating disc 3 turns discs 3, 2 and 1. The order of rotations cycles disc 1, disc 2, disc 3. The base board (ring 4 and everything not on a disc) never rotates.
- **BOARD-12** Disc 1 covers ring 1 only. Disc 2 covers rings 1 and 2. Disc 3 covers rings 1 to 3. The base covers rings 1 to 4. At ring R and a board sector, the space is the cell of the top-most disc whose cell is not a cutout, looking at discs R, R+1, ..., 3 and then the base. (Disc numbers below R do not reach ring R.) A cutout is not a space.
- **BOARD-13** Cell types: planet (name), Earth, comet, asteroids, plain space, cutout. Planets (not Earth) and comets carry a publicity icon; asteroids and plain spaces do not (MOVE-05, TECH-PT03).
- **BOARD-14** (owner, A-007) Uranus and Neptune are on the base board (ring 4). 'Oumuamua, when discovered, is placed on disc 3, ring 3, slot 3 (two sectors clockwise of Jupiter), which is a cutout before that.
- **BOARD-15** (owner, A-007) The Sun is not a space. The sector layout and the disc rotations at game start are random, from the seeded generator (A-004).
- **BOARD-16** (confirmed by the owner, clarified 2026-10-12) Adjacency: visible spaces are adjacent when in the same ring and neighbouring sectors, or in the same sector and neighbouring rings. Not diagonal. A cutout is not a space. Within every ring, sector 7 and sector 0 are neighbours (rings are circular). "No wrap-around" means only that a probe cannot leave the map: there is nothing beyond ring 4 and no move from the outer edge to the other side of the board.

## Wheels

### Disc 1

| Ring | slot 0 | slot 1 | slot 2 | slot 3 | slot 4 | slot 5 | slot 6 | slot 7 |
|---|---|---|---|---|---|---|---|---|
| 1 | cutout | Venus | Empty | Mercury | cutout | cutout | Empty | Earth |

### Disc 2

| Ring | slot 0 | slot 1 | slot 2 | slot 3 | slot 4 | slot 5 | slot 6 | slot 7 |
|---|---|---|---|---|---|---|---|---|
| 1 | Asteroid | Empty | cutout | cutout | cutout | Empty | Asteroid | Empty |
| 2 | cutout | Mars | cutout | cutout | cutout | Asteroid | Empty | cutout |

### Disc 3

| Ring | slot 0 | slot 1 | slot 2 | slot 3 | slot 4 | slot 5 | slot 6 | slot 7 |
|---|---|---|---|---|---|---|---|---|
| 1 | Empty | Asteroid | Asteroid | Empty | cutout | cutout | Asteroid | Comet |
| 2 | Comet | Asteroid | cutout | Empty | Asteroid | cutout | Empty | cutout |
| 3 | cutout | Saturn | cutout | cutout | Empty | Jupiter | Empty | cutout |

### Base board

| Ring | slot 0 | slot 1 | slot 2 | slot 3 | slot 4 | slot 5 | slot 6 | slot 7 |
|---|---|---|---|---|---|---|---|---|
| 1 | Comet | Comet | Empty | Asteroid | Asteroid | Empty | Comet | Asteroid |
| 2 | Empty | Asteroid | Empty | Comet | Empty | Asteroid | Comet | Empty |
| 3 | Asteroid | Empty | Empty | Asteroid | Asteroid | Comet | Asteroid | Empty |
| 4 | Comet | Empty | Comet | Empty | Neptune | Empty | Empty | Uranus |
