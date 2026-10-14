import { cardName } from "@/lib/moves";
// The state of a game as one viewer sees it: players, hand, card row, sectors, planets and species. It only shows what the engine's view
// contains (hidden cards are "?"); it works out no rule. Used by the live game page and by the replay.
import type { View } from "@seti/protocol";
import { CardImage } from "./CardImage";
import { SolarSystem } from "./SolarSystem";

const PLANETS = ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "oumuamua"];

export function StateView({ view, names }: { view: View; names: string[] }) {
  const s = view.state;
  const me = view.viewer;
  const who = (i: number): string => (s.rival && i === s.rival.index ? "Rival" : (names[i] ?? `Player ${i + 1}`));
  return (
    <>
      <section className="card">
        <div className="kv">
          <span>
            <b>Round</b>
            {s.round} of 5
          </span>
          <span>
            <b>Phase</b>
            {s.phase}
          </span>
          <span>
            <b>To act</b>
            {view.to_act === null ? "nobody" : who(view.to_act)}
          </span>
          <span>
            <b>Deck</b>
            {view.counts.deck} cards
          </span>
        </div>
      </section>

      <section className="grid">
        {s.players.map((p) => (
          <div key={p.index} className={`card ${view.to_act === p.index ? "turn" : ""}`}>
            <h3>
              {who(p.index)} {me === p.index ? <span className="pill">you</span> : null}{" "}
              {s.current_player === p.index ? <span className="pill">first in turn</span> : null}
              {p.passed ? <span className="pill">passed</span> : null}
            </h3>
            <div className="kv">
              <span>
                <b>Score</b>
                {p.score}
              </span>
              <span>
                <b>Publicity</b>
                {p.publicity}
              </span>
              {s.rival && p.index === s.rival.index ? (
                <>
                  <span>
                    <b>Progress</b>
                    {s.rival.progress}
                  </span>
                  <span>
                    <b>Computer</b>
                    {s.rival.computer}/6
                  </span>
                </>
              ) : (
                <>
                  <span>
                    <b>Credits</b>
                    {p.credits}
                  </span>
                  <span>
                    <b>Energy</b>
                    {p.energy}
                  </span>
                  <span>
                    <b>Movement</b>
                    {p.movement}
                  </span>
                  <span>
                    <b>Hand</b>
                    {view.counts.hands[p.index]}
                  </span>
                </>
              )}
              <span>
                <b>Data</b>
                {p.data_pool} (computer {p.computer.filter(Boolean).length}/6)
              </span>
              <span>
                <b>Probes</b>
                {s.probes.filter((x) => x.player === p.index && !x.capsule).length}
              </span>
            </div>
            <p className="small muted">
              Techs: {p.techs.join(", ") || "none"} · Tucked: {p.tucked.length} · Missions: {p.missions.length} open,{" "}
              {p.completed_missions.length} done · Sector wins: {p.sector_wins}
            </p>
          </div>
        ))}
      </section>

      {me !== null && s.players[me] ? (
        <section className="card">
          <h3>Your hand</h3>
          <div className="cards">
            {s.players[me]?.hand.length ? (
              s.players[me]?.hand.map((c) => <CardImage key={c} id={c} width={130} />)
            ) : (
              <span className="muted">empty</span>
            )}
          </div>
          {s.players[me]?.missions.length ? (
            <>
              <p className="small muted">Open missions</p>
              <div className="cards">
                {s.players[me]?.missions.map((m) => (
                  <CardImage
                    key={m.card}
                    id={m.card}
                    width={110}
                    title={`${cardName(m.card)}: ${m.kind === "trigger" ? `${m.used.filter(Boolean).length}/${m.used.length} circles` : "quick mission"}`}
                  />
                ))}
              </div>
            </>
          ) : null}
        </section>
      ) : null}

      <section className="card">
        <h3>Card row</h3>
        <div className="cards">
          {s.card_row.length ? s.card_row.map((c) => <CardImage key={c} id={c} width={130} />) : <span className="muted">empty</span>}
        </div>
      </section>

      <section className="card">
        <h3>Sectors</h3>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Star</th>
              <th>Color</th>
              <th>Data left</th>
              <th>Markers</th>
              <th>Won by</th>
            </tr>
          </thead>
          <tbody>
            {s.sectors.map((sec, i) => (
              <tr key={sec.star}>
                <td>{i}</td>
                <td>{sec.star}</td>
                <td>{sec.color}</td>
                <td>
                  {sec.data_remaining}/{sec.capacity}
                </td>
                <td>{sec.markers.map(who).join(", ") || "-"}</td>
                <td>{sec.winners.map(who).join(", ") || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="grid">
        <div className="card wide">
          <h3>Solar system</h3>
          <SolarSystem state={s} who={who} />
        </div>
        <div className="card">
          <h3>Planets</h3>
          <ul>
            {PLANETS.filter((n) => s.planets[n]).map((n) => {
              const pl = s.planets[n];
              return (
                <li key={n}>
                  {n}: orbiters {pl?.orbiters.map(who).join(", ") || "-"}; landers {pl?.landers.map(who).join(", ") || "-"}
                </li>
              );
            })}
          </ul>
        </div>
        <div className="card">
          <h3>Alien species</h3>
          {s.species.map((sp, i) => (
            <p key={`${sp.species}-${i}`}>
              {sp.discovered ? sp.species : "Undiscovered"}: discovery spaces {sp.discovery_spaces.map((d) => d ?? "·").join(" ")}; overflow{" "}
              {sp.overflow.length}
            </p>
          ))}
        </div>
        <div className="card">
          <h3>Gold scoring tiles</h3>
          {s.gold_tiles.map((g) => (
            <p key={g.tile}>
              {g.tile} ({g.side}): {g.markers.map(who).join(", ") || "no marker yet"}
            </p>
          ))}
        </div>
      </section>

      {s.objectives ? (
        <section className="card">
          <h3>Objectives</h3>
          <p>{s.objectives.row.join(" · ") || "none"}</p>
          <p className="small muted">
            {s.objectives.pile.length} completed, {view.counts.objective_stack} in the stack
          </p>
        </section>
      ) : null}
    </>
  );
}
