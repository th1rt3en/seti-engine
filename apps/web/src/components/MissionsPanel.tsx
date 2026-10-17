// The open missions of every player, face up for everybody (CARD-10 to CARD-16): a mission with circles shows which of them are covered, a quick
// mission shows that it still waits for its condition. The covered circles are filled, so what has been taken is visible to all.
import { PLAYER_COLOR } from "@/lib/geometry";
import { MISSION_CIRCLES } from "@/lib/missionCircles";
import { cardName } from "@/lib/moves";
import type { View } from "@seti/protocol";
import { CardImage } from "./CardImage";
import { CoverMarker } from "./CoverMarker";
import { type PieceColor, pieceColor } from "./Pieces";

type Mission = View["state"]["players"][number]["missions"][number];

/** One mission card with its circles: filled where covered, open where still to be covered. */
export function MissionCard({
  mission,
  size = "mission",
  color = "white",
}: { mission: Mission; size?: "mission" | "hand" | "row"; color?: PieceColor }) {
  const places = MISSION_CIRCLES[mission.card];
  const done = mission.used.filter(Boolean).length;
  const trigger = mission.kind === "trigger";
  const label = trigger ? `${done} of ${mission.used.length} circles covered` : "quick mission: its condition is not met yet";
  return (
    <figure className="missioncard" title={`${cardName(mission.card)}: ${label}`}>
      <span className="missionpic">
        <CardImage id={mission.card} size={size} />
        {/* the owner's marker lies on each circle that has been covered */}
        {places
          ? mission.used.map((u, i) => {
              const at = places[i];
              return u && at ? <CoverMarker key={`m${at.x}`} x={at.x} y={at.y} color={color} title={`Circle ${i + 1} is covered`} /> : null;
            })
          : null}
      </span>
      <figcaption className="circles" aria-label={label}>
        {trigger ? (
          mission.used.map((u, i) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: the circles of a card are fixed
            <span key={i} className={u ? "circle taken" : "circle"} title={u ? `Circle ${i + 1} is covered` : `Circle ${i + 1} is free`}>
              {u ? "●" : "○"}
            </span>
          ))
        ) : (
          <span className="muted small">quick mission</span>
        )}
      </figcaption>
    </figure>
  );
}

export function MissionsPanel({ view, names }: { view: View; names: string[] }) {
  const s = view.state;
  const players = s.players.filter((p) => !(s.rival && p.index === s.rival.index));
  if (!players.some((p) => p.missions.length > 0 || p.completed_missions.length > 0)) return null;
  return (
    <section className="card exppanel missionspanel" aria-label="Missions of all players">
      <h3>Missions</h3>
      {players.map((p) => (
        <div key={p.index} className="missionrow">
          <b className="small">
            <span className="dot small" style={{ background: PLAYER_COLOR[p.color] ?? "#fff" }} />{" "}
            {names[p.index] ?? `Player ${p.index + 1}`}
            {p.index === view.viewer ? " (you)" : ""}
          </b>{" "}
          <span className="muted small">{p.completed_missions.length} completed</span>
          <div className="missioncards">
            {p.missions.length === 0 ? <span className="muted small">no open mission</span> : null}
            {p.missions.map((m) => (
              <MissionCard key={m.card} mission={m} color={pieceColor(p.color)} />
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
