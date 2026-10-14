# Card verification summary

**Correction, 2026-10-13.** The card tracker did not show the effects of the 81 cards listed below as differences, because my extraction script missed effects written on a single line. The owner's notes were written against a tracker that showed those cards with no effects. After re-reading the repo with a correct parser (`tools/card-tracker/resolve_cards.py`), the repo already stores every effect the notes list for 66 of the 81 cards. The remaining 15 are the Exertian cards ET.41 to ET.55, for which the repo has no danger value and no end-of-game rule. The notes below are therefore still correct as a transcription of the physical cards, and the repo is more complete than this summary first suggested. The full comparison is in `data/card-definitions.json` and in the re-check page built from it.

Snapshot of the owner's checks in the card tracker, taken 2026-10-12 (`docs/spec/data/card-verification.json` holds every row). A check compares the repo's card data with the physical card.

## Result

| Group | Confirmed | Differences | Total |
|---|---|---|---|
| Base main deck | 86 | 52 | 138 |
| Base alien species cards | 28 | 27 | 55 |
| Solo rival action cards (rewritten from the card art) | 19 | 0 | 19 |
| Promo cards SE EN 01 and 02 | 2 | 0 | 2 |

Not yet checked: all expansion cards, organizations and quick start cards (deprioritized, PLAN.md D22).

## What the differences are

Every difference note describes information that is on the physical card and missing from the repo data. The notes do not describe anything the repo has wrong.

- **instant effect missing:** 60 cards
- **danger value and end-game scoring missing:** 15 cards
- **advanced action/income effect missing:** 3 cards
- **quick mission missing:** 1 card
- **other effect missing:** 1 cards

The repo draws many cards from its sprite image and stores only part of the effect in its data, so the engine cannot use the repo data as it stands for these cards.

## Notes the owner wrote, per card

### Base main deck

- **14** Mars Science Laboratory: missing instant effect: gain 1 publicity and 2 data
- **19** Gravitational Slingshot: missing instant effect: move 2
- **20** Mercury Flyby: missing instant effect: move 2
- **21** Venus Flyby: missing instant effect: move 2
- **22** Mars Flyby: missing instant effect: move 2
- **23** Jupiter Flyby: missing instant effect: move 2
- **24** Saturn Flyby: missing instant effect: move 3
- **25** Lightsail: missing instant effect: move 4
- **26** Through the Asteroid Belt: missing instant effect: move 2
- **27** Hubble Space Telescope: missing instant effect: move 1
- **28** Kepler Space Telescope: missing instant effect: move 1
- **29** James Webb Space Telescope: missing instant effect: move 1
- **45** Allen Telescope Array: Missing instant effect: scan 2 from display cards
- **46** ALMA Observatory: Missing instant effect: scan 2 from display cards
- **47** Very Large Array: Missing instant effect: scan 2 from display cards
- **48** Breakthrough Starshot: Missing instant effect: move 1, scan red
- **49** Breakthrough Watch: Missing instant effect: move 1, scan yellow
- **50** Square Kilometre Array: Missing instant effect: scan 3 from display cards
- **52** Parkes Observatory: missing instant effect: scan action
- **53** Deep Synoptic Array: missing instant effect: scan action
- **54** VERITAS Telescopes: missing instant effect: scan action
- **55** Arecibo Observatory: missing instant effect: scan action
- **56** Breakthrough Listen: missing instant effect: move 1, scan blue
- **57** Effelsberg Telescope Construction: missing instant effect: 1 card any, 1 rotate, 1 pink technology
- **59** Ion Propulsion System: missing instant effect: 1 energy, 1 rotate, 1 orange technology
- **65** FAST Telescope Construction: missing instant effect: scan 2 from display cards, 1 rotate, 1 pink technology
- **67** Yevpatoria Telescope Construction: missing instant effect: 1 publicity, 1 rotate, 1 pink technology
- **71** Focused Research: missing instant effect: 1 rotate, 1 any color technology
- **72** Scientific Cooperation: missing instant effect:, 1 rotate, 1 any color technology
- **74** Pre-launch Testing: missing instant effect: 1 launch action
- **75** Extremophiles Study: missing instant effect: 1 any trace
- **81** International Collaboration: missing instant effect:  1 any color technology
- **83** Wow! Signal: missing instant effect: 1 publicity, mark 2 signals
- **85** Starship: missing instant effect: 1 launch action, 1 rotate, 1 orange technology
- **86** Giant Magellan Telescope: missing instant effect: scan 1 from display cards
- **92** NASA Image of the Day: missing instant effect: 2 publicity
- **105** Green Bank Telescope: missing instant effect: 1 scan action; missing quick mission: mark 3 pink traces -> mark 1 pink trace
- **109** Low-Power Microprocessors: missing instant effect: 1 energy, 1 rotate, 1 blue technology
- **110** Press Statement: missing instant effect: 3 publicity
- **113** Solvay Conference: missing instant effect: 2 publicity
- **114** Planet Hunters: missing instant effect: draw 1 any
- **118** PLATO: missing instant effect: mark 3 signals
- **119** PIXL: missing instant effect:  1 rotate, 1 blue technology
- **121** Future Circular Collider: missing instant effect: 3 data, 1 rotate, 1 blue technology
- **123** Asteroids Flyby: missing instant effect: move 1
- **124** Cometary Encounter: missing instant effect: move 2
- **125** Trajectory Correction: missing instant effect: move 1
- **127** NEAR Shoemaker: missing instant effect: 2 publicity
- **130** Low-Cost Space Launch: missing instant effect: 1 launch action
- **133** Optimal Launch Window: missing instant effect: 1 launch action
- **135** Noto Radio Observatory: missing instant effect: 1 publicity, 1 scan action
- **137** SETI Data Archive: missing instant effect: 2 data

### Alien species cards

- **ET.11** Signs of Life: missing instant effect: 1 launch action
- **ET.12** Close-up View: missing instant effect: move 5
- **ET.15** Part of Everyday Life: missing instant effect: draw 3
- **ET.18** Message Capsule: missing instant effect: 1 rotate, 1 any technology
- **ET.19** New Physics: missing instant effect: 1 any trace
- **ET.20** Amazing Uncertainty: missing instant effect: mark 1 signal
- **ET.25** Probe Customisation: missing effect: then land (after movement).
- **ET.26** Race Against Time: missing instant effect: 1 launch action, 1 exofossil
- **ET.28** Exofossil Samples: missing instant effect: 1 rotate, 1 blue tech
- **ET.31** Vessel Designs: missing effect: e.ADVANCED_15(), 1 launch action, e.FULFILL_ADVANCED(), e.INCOME()
- **ET.32** Exocomputers: missing effect: e.ADVANCED_15(), 2 data, e.FULFILL_ADVANCED(), e.INCOME()
- **ET.34** A Message from Afar: missing effect: e.ADVANCED_15(), draw 1, e.FULFILL_ADVANCED(), mark 1 pink trace
- **ET.41** Razor-edge Shuttle: missing effect: danger 6, endgame scoring: 3 orange tech -> 14 score
- **ET.42** Deflector: missing effect: danger 7, endgame scoring: 3 pink tech -> 15 score
- **ET.43** Expender Core: missing effect: danger 3, endgame scoring: 3 blue tech -> 9 score
- **ET.44** pierced Exoplanet: missing effect: danger 4, endgame scoring: 2 red sector victories -> 12 score
- **ET.45** Core-breach Exoplanet: missing effect: danger 4, endgame scoring: 2 blue sector victories -> 12 score
- **ET.46** Vortex Exoplanet: missing effect: danger 4, endgame scoring: 2 yellow sector victories -> 12 score
- **ET.47** Fission-sun Exoplanet: missing effect: danger 5, endgame scoring: 2 black sector victories -> 14 score
- **ET.48** Oscillating Probes: missing effect: danger 3, endgame scoring: 3 probes in orbit -> 11 score
- **ET.49** Generative Infrastructure: missing effect: danger 7, endgame scoring: 4 landers (including moons) -> 16 score
- **ET.50** Casette Deployment: missing effect: danger 2, endgame scoring: 3 orbiters or landers at a single planet (including moons) -> 10 score
- **ET.51** Extractor: missing effect: danger 8, endgame scoring: 8 cards tucked for income -> 18 score
- **ET.52** Automated Lab: missing effect: danger 0, endgame scoring: marked 6 traces of exertians -> 7 score
- **ET.53** Neuralab: missing effect: danger 9, endgame scoring: marked 6 traces of the other species -> 20 score
- **ET.54** Nanowielder Node: missing effect: danger 1, endgame scoring: marked 5 or more traces of the same color -> 8 score
- **ET.55** Stratoelevator: missing effect: danger 4, endgame scoring: finished 5 or more quick missions -> 12 score

## What this means for the engine

- 138 base cards: 86 repo entries are complete as they are. 52 need the missing effect added.
- 55 alien cards: 28 are complete and 27 need the missing effect. 15 of those (ET.41 to ET.55) lack the danger value and the end-game scoring formula.
- The engine's card definitions should be built as: repo data, plus the owner's notes as corrections, in one structured format. This is Phase 2 work.
- Rival cards: the rewritten data in `docs/spec/data/rival-action-cards.json` is confirmed and replaces the repo data.
