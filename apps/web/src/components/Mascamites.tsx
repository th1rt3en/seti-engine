// The Mascamite species (ALIEN-MASC-01 to ALIEN-MASC-05) in the page: the reward of a sample when a choice is offered, and the tab of the
// hand panel with the samples on the planets, the sample spaces of the species board and the player's own capsules. It works out no rule.
import { cardName } from "@/lib/moves";
import type { View } from "@seti/protocol";
import { Rewards } from "./Reward";

type Reward = { t: string; n: number };
type SampleSpace = { token: number; marker: number | null; reward: Reward[] };

/** What the sample behind a choice gives (the engine's note of the move). */
export function SampleReward({ note }: { note: unknown }) {
  const rewards = (note as { rewards?: Reward[] } | null | undefined)?.rewards;
  return rewards ? (
    <span className="samplereward">
      {" "}
      <Rewards list={rewards} size={16} />
    </span>
  ) : null;
}

export function MascamiteTab({ view, who }: { view: View; who: (seat: number) => string }) {
  const s = view.state;
  const me = view.viewer;
  const slot = s.species.find((sp) => sp.discovered && sp.species === "mascamites");
  if (!slot) return null;
  const onPlanets = (slot.extra.samples ?? {}) as Record<string, number[]>;
  const spaces = (slot.extra.sample_spaces ?? []) as SampleSpace[];
  const capsules = s.probes.filter((p) => p.capsule);
  const mine = capsules.filter((p) => p.player === me);
  const deliveries = view.legal.filter((m) => m.type === "deliver_sample");
  const player = me === null ? undefined : s.players[me];
  const deliverMissions = player?.missions.filter((m) => m.kind === "deliver") ?? [];
  return (
    <div className="mascamitetab">
      <p>
        <b>Samples on the planets (face down):</b>{" "}
        {Object.entries(onPlanets)
          .map(([planet, tokens]) => `${planet.charAt(0).toUpperCase()}${planet.slice(1)} ${tokens.length}`)
          .join(" · ")}
      </p>
      <div>
        <b>Sample spaces of the species board:</b>
        <ul className="samplespaces">
          {spaces.map((sp, j) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: the spaces fill in order
            <li key={j} className={sp.marker === null ? undefined : "taken"}>
              Space {j + 1}: <Rewards list={sp.reward} size={16} />{" "}
              {sp.marker === null ? <span className="muted">free to mark</span> : <span>marked by {who(sp.marker)}</span>}
            </li>
          ))}
        </ul>
      </div>
      <div>
        <b>Sample capsules on the map:</b>
        {capsules.length === 0 ? <span className="muted"> none</span> : null}
        <ul className="capsules">
          {capsules.map((c) => {
            const note = view.notes[view.legal.findIndex((m) => m.type === "deliver_sample" && m.capsule === c.id)];
            return (
              <li key={c.id}>
                {who(c.player)}: capsule {c.id} (ring {c.ring}, sector {c.sector})
                {c.player === me && c.sample !== null && c.sample !== undefined && c.sample >= 0 ? (
                  <span> carries a sample (see the delivery below)</span>
                ) : null}
                {c.player !== me ? <span className="muted"> carries a face-down sample</span> : null}
                {note ? <SampleReward note={note} /> : null}
              </li>
            );
          })}
        </ul>
      </div>
      {player ? (
        <p>
          <b>Your delivery missions:</b>{" "}
          {deliverMissions.length === 0
            ? "none"
            : deliverMissions
                .map((m) => `${cardName(m.card)}${deliveries.some((d) => d.card === m.card) ? " (a capsule is there: deliver it)" : ""}`)
                .join("; ")}
          {mine.length > 0 ? ` · you have ${mine.length} capsule${mine.length === 1 ? "" : "s"}` : ""}
        </p>
      ) : null}
    </div>
  );
}
