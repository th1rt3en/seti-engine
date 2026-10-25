"use client";
// The samples on a planet (Mascamites, ALIEN-MASC-02, FAQ-C201): after the planet is picked, a panel shows each sample with what it gives, and the player picks
// one and confirms. A card that looks at the samples (ET.8) gives the reward of the one picked and puts it back; collecting takes it.
import assets from "../generated/assets.json";
import { Rewards } from "./Reward";

type Reward = { t: string; n: number };

export interface SampleChoice {
  /** The token (its place among the seven tokens of the species). */
  token: number;
  rewards: Reward[];
}

const FACE = assets.samples as Record<string, string>;

export function SamplePanel({
  planet,
  mode,
  samples,
  selected,
  onSelect,
  onConfirm,
  onBack,
}: {
  planet: string;
  mode: "peek" | "collect";
  samples: SampleChoice[];
  selected: number | null;
  onSelect: (token: number) => void;
  onConfirm: () => void;
  /** Present when the planet was picked among several: back to the choice of the planet. */
  onBack?: () => void;
}) {
  const name = planet.charAt(0).toUpperCase() + planet.slice(1);
  return (
    <section className="offerpanel samplepanel" aria-label={`The samples on ${name}`}>
      <h2>Samples on {name}</h2>
      <p className="muted small">
        {mode === "peek"
          ? "You look at the samples: pick one to gain its reward. The sample goes back where it was."
          : "Pick the sample to collect: it is taken from the planet."}
      </p>
      <div className="offercards">
        {samples.map((s) => (
          <button
            key={s.token}
            type="button"
            className={s.token === selected ? "offercard chosen" : "offercard"}
            aria-pressed={s.token === selected}
            onClick={() => onSelect(s.token)}
          >
            <span className="samplechoice">
              <img src={FACE[String(s.token)]} alt={`Sample ${s.token + 1}`} width={110} height={110} />
              <Rewards list={s.rewards} size={20} />
            </span>
          </button>
        ))}
      </div>
      <div className="samplebuttons">
        {onBack ? (
          <button type="button" className="secondary" onClick={onBack}>
            Another planet
          </button>
        ) : null}
        <button type="button" className="primary" disabled={selected === null} onClick={onConfirm}>
          {selected === null ? "Pick a sample" : mode === "peek" ? "Gain its reward" : "Collect it"}
        </button>
      </div>
    </section>
  );
}
