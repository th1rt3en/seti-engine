# Space Agencies expansion: organization and quick start data

Data, not rules (see `expansion.md`). Source: the repository's card extraction `tools/card-tracker/cards-extracted.json` (a community transcription of the cards, with the ability texts and a reference summary); machine-readable copies are `data/expansion-organizations.json` and `data/expansion-quick-start.json`. The starting resources, tuck icons, incomes and ability texts of the organizations were compared on 2026-10-15 with the pictures of the cards in the rulebook (R16 p.2 and p.5) and agree; the owner has not checked them yet. The quick start cards are not shown in the rulebook pictures in a readable size: owner check pending. Resources are the starting resources at the top of the organization card; "tuck" is how many cards the organization lets the player tuck for income at the start (EXP-ORG-07); "income" is what the organization gives at the start of rounds 3, 4 and 5 (EXP-ORG-08); a signal token income is the new resource of EXP-SIG-01.

## Organizations (11)

| No. | Organization | Credits | Energy | Cards | Publicity | Data | Probes | Tuck | Income: credit / energy / card / publicity / data / signal |
|---|---|---|---|---|---|---|---|---|---|
| 6 | Cosmos Strategy Group | 4 | 2 | 1 | 1 | 0 | 0 | 2 | 2 / 1 / 1 / 0 / 0 / 0 |
| 4 | Deep Sky Survey | 3 | 2 | 0 | 3 | 1 | 0 | 2 | 2 / 2 / 1 / 0 / 0 / 1 |
| 2 | Fenwick Research Center | 3 | 1 | 0 | 4 | 0 | 0 | 3 | 3 / 1 / 0 / 1 / 0 / 0 |
| 10 | Futurespan Institute | 3 | 3 | 1 | 3 | 0 | 0 | 2 | 2 / 1 / 1 / 0 / 0 / 0 |
| 11 | Helion Assembly | 3 | 2 | 0 | 7 | 0 | 0 | 0 | 3 / 1 / 1 / 1 / 0 / 0 |
| 8 | Mission Relay | 3 | 2 | 2 | 2 | 0 | 0 | 3 | 1 / 1 / 1 / 0 / 0 / 0 |
| 1 | Orbital Dynamics | 2 | 2 | 0 | 3 | 0 | 2 | 2 | 3 / 1 / 1 / 0 / 0 / 0 |
| 7 | Sentinel Probe Network | 4 | 2 | 0 | 3 | 0 | 0 | 1 | 3 / 1 / 1 / 0 / 0 / 1 |
| 3 | Stratus Core | 3 | 2 | 1 | 3 | 0 | 0 | 3 | 2 / 1 / 1 / 0 / 0 / 0 |
| 5 | Turing Systems | 4 | 2 | 1 | 2 | 0 | 0 | 2 | 2 / 2 / 1 / 0 / 1 / 0 |
| 9 | Xenolab | 2 | 2 | 1 | 1 | 0 | 0 | 3 | 2 / 1 / 1 / 0 / 0 / 0 |

### Abilities

- **Cosmos Strategy Group** (`cosmos_strategy_group`)
  - passive: When you play a card as a main action, you may mark one matching reward space if the card's sector color matches an unmarked space on this organization. Yellow or black cards can mark the credit space, red or black cards can mark the publicity space, and blue or black cards can mark the data space.
  - freeAction: Once per round, gain 1 card from either the card row or the top of the deck, then clear all reward spaces marked on this organization.
- **Deep Sky Survey** (`deep_sky_survey`)
  - passive: You don't need energy to perform Analyze Data.
  - freeAction: Once per round, switch a card from your hand with a card on the card row.
- **Fenwick Research Center** (`fenwick_research_center`)
  - passive: You only need 5 publicity to research tech.
  - freeAction: Once per round, spend 1 publicity to gain any card from the card row or a random card from the main deck, then gain that card's free-action corner bonus.
- **Futurespan Institute** (`futurespan_institute`)
  - freeAction: Prepare one card from your hand by placing it on this organization and setting the countdown to that card's credit cost x 10 + 5. Once per round while the token is on the scoring track, move it 3 spaces farther ahead and gain 1 card.
  - mainAction: Once your score marker reaches or passes the Futurespan token, play the prepared card as a main action without paying its credit cost, then return the token.
- **Helion Assembly** (`helion_assembly`)
  - passive: When you develop a tech, you may mark the matching reward space on this organization and gain its reward. Probe/orange tech grants 1 energy, scan/purple tech grants 1 signal token, and computer/blue tech grants 1 data.
  - freeAction: Once per round, destroy one of your probe/orange or scan/purple techs, then tuck one card from your hand for income and clear all reward spaces marked on this organization.
- **Mission Relay** (`mission_relay`)
  - setup: At the start of the game, mark the lowest-scoring space on the mission gold scoring tile.
  - passive: When you play a card with a mission, gain 1 publicity.
  - freeAction: Once per round, spend 2 publicity to gain any card from the card row or a random card from the main deck, then immediately gain the resource matching that card's income corner.
- **Orbital Dynamics** (`orbital_dynamics`)
  - passive: Your probe capacity is 1 higher.
  - freeAction: Once per round, move at most 2 different probes of yours with 1 step each.
- **Sentinel Probe Network** (`sentinel_probe_network`)
  - passive: When you launch a probe, mark a signal in that probe's sector.
  - freeAction: Once per round, after you play and fully resolve a non-alien card as a main action this turn, gain that card's free-action corner effect.
- **Stratus Core** (`stratus_core`)
  - freeAction: Once per round, gain the free-action corner effects of all 3 cards in the card row without discarding those cards.
- **Turing Systems** (`turing_systems`)
  - passive: When you research a computer/blue tech, gain 1 publicity.
  - freeAction: Once per round, choose any probe or scan tech. Until the end of this turn, you may use that tech's ability as if you had researched it. This does not count as researching the tech and does not grant its immediate bonuses.
- **Xenolab** (`xenolab`)
  - mainAction: Xenolab starts with three active action tiles. You may use an active tile as a discounted main action, then flip that tile inactive: spend 1 credit to launch a probe, spend 2 energy to scan, or spend 4 publicity to research any tech.
  - passive: When you gain the trace shown on an inactive tile, flip that tile back active. The trace is still gained normally and is not spent.

## Quick start cards (21)

| Card | Top half (mark without any benefit) | Bottom half |
|---|---|---|
| SR.1 | a yellow trace in the discovery space of the right species | 3 score, 1 publicity |
| SR.2 | a pink trace in the discovery space of the right species | 3 score, 1 publicity |
| SR.3 | 2 signal(s) in Barnard's Star | 2 score, 2 data |
| SR.4 | 2 signal(s) in Proxima Centauri | 2 score, 2 data |
| SR.5 | 2 signal(s) in Sirius A | 2 score, 2 data |
| SR.6 | 2 signal(s) in Procyon | 2 score, 2 data |
| SR.7 | 2 signal(s) in Kepler 22 | 2 score, 2 data |
| SR.8 | 2 signal(s) in 61 Virginis | 2 score, 2 data |
| SR.9 | 2 signal(s) in Beta Pictoris | 2 score, 2 data |
| SR.10 | 1 signal(s) in Vega | 1 signal token, 1 data |
| SR.11 | an orbiter at Saturn | 4 score, 2 publicity |
| SR.12 | an orbiter at Venus | 3 score, 1 publicity, 1 energy |
| SR.13 | an orbiter at Jupiter | 3 score, 1 publicity, 1 data |
| SR.14 | an orbiter at Mercury | 2 score, 1 publicity, 1 credit |
| SR.15 | an orbiter at Uranus | tuck this card to increase your card income and gain 1 card at once |
| SR.16 | an orbiter at Neptune | tuck this card to increase your data income and gain 1 data at once |
| SR.17 | an orbiter at Mars | 3 score, 1 publicity, 1 card |
| SR.18 | - | 3 score, 1 credit, 1 card |
| SR.19 | - | 3 score, 1 energy, 1 card |
| SR.20 | - | 4 score, 1 signal token, 1 publicity |
| SR.21 | - | 3 score, 3 publicity |

## Not in the data (see ambiguities.md)

- The 42 main-deck cards: only about a third have their effects in the extraction, the rest are in the pictures (A-028).
- The 20 alien cards of the three species and the Arkhos exploration (9) and security (12) cards (A-032).
- The boards of the three species, the translation strips, the organelle layout (A-032).
- The 4 solo rival cards and the 3 long-term objective tiles (A-033, A-034).
