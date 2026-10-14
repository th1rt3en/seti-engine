// Words for the engine's events in the replay. The engine decides what happened; this only turns its event records into a line of text.
export type GameEvent = { type: string } & Record<string, unknown>;

const words = (s: string): string => s.replace(/_/g, " ");

export function describeEvent(e: GameEvent, who: (i: number) => string): string {
  const { type, player, ...rest } = e;
  const head = typeof player === "number" ? `${who(player)}: ${words(type)}` : words(type);
  const details = Object.entries(rest)
    .filter(([, v]) => v !== null && v !== undefined && typeof v !== "object")
    .map(([k, v]) => `${words(k)} ${String(v)}`);
  return details.length > 0 ? `${head} (${details.join(", ")})` : head;
}
