import { BoardView } from "@/components/BoardView";
import type { View } from "@seti/protocol";
import sample from "../../generated/sample-view.json";

export default function Page() {
  const view = structuredClone(sample) as unknown as View;
  const sp = view.state.species[0];
  if (sp) {
    sp.discovered = true;
    sp.species = "exertians";
    sp.extra = { milestones: [{ at: 40, cost: 0, done: [] }, { at: 60, cost: 1, done: [] }] };
  }
  const second = view.state.species[1];
  if (second) { second.discovered = true; second.species = "centaurians"; }
  view.state.players.forEach((p, i) => { (p as unknown as { messages: number[] }).messages = [20 + i * 7]; });
  return <BoardView view={view} names={["A", "B", "C"]} />;
}
