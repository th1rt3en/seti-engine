// Where the last move of the game left its mark on the board: the sectors where a signal was marked or a sector was won, the spaces a probe moved to,
// and the planets that were orbited or landed on. It is read from the events of the last entry of the log (so it also shows after a refresh or a
// reconnection), and it says only where to look: the board is drawn from the state.
export interface LastMove {
  sectors: number[];
  cells: [number, number][];
  planets: string[];
}

interface EventLike {
  type: string;
  sector?: unknown;
  to?: unknown;
  planet?: unknown;
}

export function lastMoveOf(events: EventLike[] | undefined): LastMove | null {
  if (!events || events.length === 0) return null;
  const sectors: number[] = [];
  const cells: [number, number][] = [];
  const planets: string[] = [];
  for (const e of events) {
    if ((e.type === "signal" || e.type === "sector_won") && typeof e.sector === "number" && !sectors.includes(e.sector))
      sectors.push(e.sector);
    if (e.type === "move" && Array.isArray(e.to) && e.to.length === 2) cells.push([Number(e.to[0]), Number(e.to[1])]);
    if ((e.type === "orbit" || e.type === "land") && typeof e.planet === "string" && !planets.includes(e.planet)) planets.push(e.planet);
  }
  return sectors.length + cells.length + planets.length === 0 ? null : { sectors, cells, planets };
}
