// A design preview of the game page with a sample game (no sign-in, no server): `tools/web/make_sample_view.py` makes the sample.
import { GameView } from "@/components/GameView";
import type { View } from "@seti/protocol";
import sample from "../../generated/sample-view.json";

export const metadata = { title: "Game page preview" };

export default function Demo() {
  const view = structuredClone(sample) as unknown as View;
  // the sample game has no discovered species: turn the first one face up (a design preview only) to show a revealed board
  // some orbiters and landers, to show the figures on the planets
  const planets = view.state.planets;
  if (planets.jupiter) {
    planets.jupiter.orbiters = [0, 1];
    planets.jupiter.landers = [2];
    planets.jupiter.moon_landers = { Io: 1 };
  }
  if (planets.mars) planets.mars.landers = [0];
  // nobody has passed yet in this round, so the moon token lies on this round's pile
  view.state.first_pass_done = false;
  const stack = view.state.tech_stacks[1];
  if (stack) stack.two_point_tile = false;
  const first = view.state.species[0];
  if (first) {
    first.discovered = true;
    first.species = "centaurians";
    first.discovery_spaces = ["p0", "n", "p2"];
    first.board = { pink: [[0], [1]], yellow: [[2]], blue: [[]] };
    // the deck of the species and the card that lies face up, and an 'Oumuamua exofossil, to show the column beside the board and the tracker row
    first.deck = Array(7).fill("?");
    first.face_up = "ET.12";
    const second = view.state.species[1];
    if (second) {
      second.discovered = true;
      second.species = "oumuamua";
      second.deck = Array(9).fill("?");
      second.face_up = "ET.31";
      second.board = { pink: [[1, 0], [2], [], [], []], yellow: [[], [], [], [], []], blue: [[0], [], [], [], []] };
      view.state.oumuamua_placed = true;
      second.extra = { tile: { data: 1, markers: [0, 1] }, supply: 15 };
      second.overflow = [0, 2];
      second.overflow_kinds = ["blue", "blue"];
    }
    for (const p of view.state.players) p.exofossils = p.index + 1;
    // Centaurian message milestones and a message card marker, to show them on the score track
    view.state.players.forEach((p, i) => {
      p.messages = [p.score + 15];
      if (i === 0) p.message_cards = [{ target: p.score + 22, card: "ET.35" }];
    });
  }
  const names = ["Alice", "Bob", "Cy"];
  return (
    <GameView
      view={view}
      names={names}
      topExtra={<span className="small muted">Sample game for the design preview</span>}
      moves={
        <div className="movegroups">
          <div className="mgroup">
            <span className="glabel">Main action</span>
            <div className="moves">
              {view.legal.slice(0, 6).map((m, i) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: a static preview
                <button key={i} type="button">
                  {String(m.type)}
                </button>
              ))}
            </div>
          </div>
        </div>
      }
    />
  );
}
