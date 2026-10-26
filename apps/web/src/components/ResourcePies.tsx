// Where each resource came from: a pie for each of credits, energy, cards, data, publicity and points, the slices being the sources (the mean per player). The
// numbers are the counters `gain.<source>.<resource>` of the engine (stats.py); a source is the part of the game that was running when the resource was gained.
import { GAIN_RESOURCES, RESOURCE_NAMES, SOURCE_COLORS, SOURCE_NAMES } from "@/lib/resources";
import type { Slice } from "@/lib/stats";
import { PieChart } from "./PieChart";
import { KindIcon } from "./Reward";
import { Panel } from "./StatCharts";

const name = (key: string): string => SOURCE_NAMES[key] ?? key.replace(/_/g, " ");

export function ResourcePies({ gains }: { gains: Record<string, Slice[]> }) {
  return (
    <>
      {GAIN_RESOURCES.map((res) => {
        const slices = gains[res] ?? [];
        return (
          <Panel
            key={res}
            title={RESOURCE_NAMES[res] ?? res}
            icon={<KindIcon kind={res} size={24} />}
            note={`Where the ${(RESOURCE_NAMES[res] ?? res).toLowerCase()} of a player came from, on average per game. Point the pie or its legend for the lowest, the highest and the spread of the players.`}
          >
            <PieChart
              label={`${RESOURCE_NAMES[res] ?? res} gained, by source`}
              slices={slices.map((x) => ({
                key: x.key,
                name: name(x.key),
                label: name(x.key),
                value: x.mean,
                spread: x.spread,
                color: SOURCE_COLORS[x.key] ?? "#8b949e",
              }))}
            />
            <p className="muted small">
              Sources that gave some: {slices.length === 0 ? "none yet" : slices.map((x) => name(x.key)).join(", ")}.
            </p>
          </Panel>
        );
      })}
    </>
  );
}
