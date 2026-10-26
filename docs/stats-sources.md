# Sources tracked by the statistics page (2026-10-26)

A **source** is the part of the game that was running when a player gained something (the engine's trail of gains, `services/engine/src/seti_engine/trail.py`,
counted in `stats.py` as `gain.<source>.<resource>`). Every gain of credits, energy, cards, data, publicity or points is recorded under exactly one source;
a gain that no inner source claims falls to the source around it, and in the end to **Main and free actions**.

| Source (page) | Engine kind | What it covers |
|---|---|---|
| Main and free actions | `move` | the action itself (launch, scan, analyze, research, pass; free actions such as moving a probe, trading, buying a card); anything not claimed by a source below |
| Playing a card | `card` | the effect of a card played as a main action |
| Free corner of a discarded card | `corner` | the free-action corner of a card discarded for it (not the signal) |
| Income of the round | `income` | the income of the round, and the income gained when a card is tucked |
| Organization | `organization` | the starting resources and the abilities of the organization (also when a card with a mission is played, Mission Relay) |
| Quick start cards | `quick_start` | the bottom half of the quick start cards |
| Missions | `mission` | completing a mission, covering a mission circle |
| Technologies | `tech` | the bonus of a tech tile, the first player to take a tech, the lower space of a computer tech |
| Marking a signal | `signal` | the reward of the space of a sector where the signal lies |
| Completing a sector | `sector` | the rewards of a completed sector (the winner, the second) |
| Life traces | `trace` | the rewards of a trace marked on a species board |
| Anomaly tokens | `anomaly` | the anomaly tokens reached by the Earth |
| Planets | `planet` | orbiting, landing, the first orbiter, the first lander's data, moons |
| Arkhos exploration | `explore` | the minor and the major exploration rewards |
| Glyphids glyphs | `glyph` | the glyph icons of cards and the translation board |
| Alien species effects | `alien` | Centaurian message milestones and message cards, Mascamite samples, Amoeba organelles |
| The rival's turn / computer | `rival_turn`, `rival_computer` | what the solo rival's turn or computer gives the player |

Publicity from moving a probe is split by what the probe moved onto: **a comet**, **an asteroid field**, **a planet**; what is left stays in Main and free actions.

Points have four more slices that are not gains but parts of the final score: **end-of-game cards**, **gold scoring tiles**, **Exertian cards**, **glyph tokens left**
(the Exertian danger loss is taken off the total and is not a slice). They come from the rows of version 3 of the statistics.

Not tracked as a source (say if one is missing): points of the gold milestones before the end (they are only marked; the tile scores at the end), exofossils,
signal tokens, movement (what resources were spent on is below).

## Cards

Version 3 of the statistics counts, for each player, every card played as a main action by the round it was played in (`card.<id>.r<round>`); the page joins
that with the final score, the win and the organization of the player's row. Exertian cards (played face down at milestones) are not part of it. The rows of
games that ended before version 3 have no cards until their statistics are made again: `python tools/engine/backfill_stats.py --all` (see its header).

## What resources were spent on (version 4)

The costs are recorded apart (`trail.cost` in the engine, the source kind `cost`) so that they do not cancel what an effect gives: the pies of what was spent
have these slices. Credits: launching probes, scanning, orbiting, playing cards, trading resources. Energy: scanning, orbiting, landing, analyzing, a probe
launched by the scan, turned into movement, trading. Publicity: researching techs, buying a card of the display, the signal in Mercury's sector. Data: placed in
the computer. Cards: played, tucked for income, discarded for their free corner, discarded for a signal, discarded down to four at the pass, traded.
Points are not spent. Not counted yet (it falls under the source around it, or nowhere): costs paid inside a card's own effect (an optional cost), the
Exertian cards' cost, the organizations' costs, and exofossils spent.

The quick start cards that a player kept are counted as `quick.<id>` (the Organization & Quickstart tab).
