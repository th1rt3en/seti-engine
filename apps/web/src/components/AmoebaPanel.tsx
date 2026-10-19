// The Amoeba board (EXP-AMO-02 to EXP-AMO-05): the five organelle tokens on the nine spaces of the cell, the markers of the players on the
// columns below it, and the places a move can be made at (the organelle that gives its bonus, the marker that is removed).
import { PLAYER_COLOR } from "@/lib/geometry";
import { SPECIES_SPACES } from "@/lib/speciesSpaces";
import { AMOEBA_SCALE, ORGANELLE_SPACES, ORGANELLE_TOKENS } from "@/lib/targets";
import type { View } from "@seti/protocol";
import expansionAssets from "../generated/expansion-assets.json";
import type { BoardSpots } from "./BoardView";
import { PanelSpots } from "./PanelSpots";

const ASSET = expansionAssets as Record<string, string>;
const TOKENS = ORGANELLE_TOKENS;
const W = 573;
const H = 1044;

export function AmoebaPanel({ view, names, spots }: { view: View; names: string[]; spots?: BoardSpots }) {
  const slot = view.state.species.find((sp) => sp.discovered && sp.species === "amoeba");
  const src = ASSET["boards/amoeba"];
  if (!slot || !src) return null;
  const organelles = (slot.extra.organelles ?? {}) as Record<string, number>;
  const board = slot.board as Record<string, number[][]>;
  const colors = ["pink", "yellow", "blue"] as const;
  return (
    <section className="card exppanel" aria-label="Amoeba board">
      <h3>Amoeba</h3>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="panelsvg"
        role="img"
        aria-label="The Amoeba board with its organelles and the markers placed"
      >
        <image href={src} x={0} y={0} width={W} height={H} />
        {Object.entries(organelles).map(([space, kind]) => {
          const at = ORGANELLE_SPACES[space];
          const href = ASSET[`tokens/organelle-token-${TOKENS[kind] ?? "back"}`];
          if (!at || !href) return null;
          return (
            <image key={space} href={href} x={at[0] - 36} y={at[1] - 36} width={72} height={72}>
              <title>{`Organelle on ${space}`}</title>
            </image>
          );
        })}
        {colors.flatMap((c) =>
          (board[c] ?? []).flatMap((owners, k) => {
            const at = SPECIES_SPACES.amoeba?.[c]?.[k];
            if (!at) return [];
            return owners.map((o, j) => (
              <circle
                key={`${c}-${k}-${j}-${o}`}
                cx={at[0] * AMOEBA_SCALE + (j - (owners.length - 1) / 2) * 26}
                cy={at[1] * AMOEBA_SCALE}
                r={14}
                fill={PLAYER_COLOR[view.state.players[o]?.color ?? ""] ?? "#fff"}
                stroke="#000"
                strokeWidth={3}
              >
                <title>{`${names[o] ?? `Player ${o + 1}`}: marker on the ${c} space ${k + 1}`}</title>
              </circle>
            ));
          }),
        )}
        <PanelSpots spots={spots} panel="amoeba" />
      </svg>
    </section>
  );
}
