// Where each resource came from and what it was spent on: two pies for each of credits, energy, cards, data, publicity and points, the slices being the sources
// and the uses (the mean per player of each). The numbers are the counters `gain.<source>.<resource>` and `spend.<what>.<resource>` of the engine (stats.py):
// a source is the part of the game that was running when the resource was gained, and a use is what a cost paid for.
import { GAIN_RESOURCES, RESOURCE_NAMES, SOURCE_COLORS, SOURCE_NAMES, SPEND_NAMES } from "@/lib/resources";
import type { Slice } from "@/lib/stats";
import { PieChart } from "./PieChart";
import { KindIcon } from "./Reward";
import { Panel } from "./StatCharts";

const PLURAL = new Set(["credit", "card", "vp", "exofossil"]); // credits, cards and points are plural
const sourceName = (key: string): string => SOURCE_NAMES[key] ?? key.replace(/_/g, " ");
const spendName = (key: string, res = ""): string =>
  res === "move" && key === "move" ? "Moving probes" : (SPEND_NAMES[key] ?? SOURCE_NAMES[key] ?? key.replace(/_/g, " "));

export function ResourcePies({ gains, spends }: { gains: Record<string, Slice[]>; spends: Record<string, Slice[]> }) {
  return (
    <>
      {GAIN_RESOURCES.map((res) => {
        const gained = gains[res] ?? [];
        const spent = spends[res] ?? [];
        if (res === "exofossil" && gained.length === 0 && spent.length === 0) return null; // only with 'Oumuamua
        const lower = (RESOURCE_NAMES[res] ?? res).toLowerCase();
        return (
          <Panel
            key={res}
            title={RESOURCE_NAMES[res] ?? res}
            icon={<KindIcon kind={res} size={24} />}
            note="Averages per player and game. Point a slice or its legend row for the lowest, the highest and the spread of the players."
            wide
          >
            <div className="pie-pair">
              <div>
                <h3>Where the {lower} came from</h3>
                <PieChart
                  label={`${RESOURCE_NAMES[res] ?? res} gained, by source`}
                  slices={gained.map((x) => ({
                    key: x.key,
                    name: sourceName(x.key),
                    label: sourceName(x.key),
                    value: x.mean,
                    spread: x.spread,
                    parts: x.parts?.map((p) => ({ name: sourceName(p.key), value: p.mean })),
                    color: SOURCE_COLORS[x.key] ?? "#8b949e",
                  }))}
                />
              </div>
              <div>
                <h3>
                  What the {lower} {PLURAL.has(res) ? "were" : "was"} spent on
                </h3>
                {res === "vp" ? (
                  <p className="muted">Points are not spent.</p>
                ) : spent.length === 0 ? (
                  <p className="muted">Nothing was spent in the games counted yet (it is counted from version 4 of the statistics).</p>
                ) : (
                  <PieChart
                    label={`${RESOURCE_NAMES[res] ?? res} spent, by use`}
                    unit="per player, spent"
                    slices={spent.map((x) => ({
                      key: x.key,
                      name: spendName(x.key, res),
                      label: spendName(x.key, res),
                      value: x.mean,
                      spread: x.spread,
                      color: SOURCE_COLORS[x.key] ?? "#8b949e",
                    }))}
                  />
                )}
              </div>
            </div>
          </Panel>
        );
      })}
    </>
  );
}
