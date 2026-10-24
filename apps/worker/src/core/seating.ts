// Seating (decision D28): who sits where is drawn when the game starts, so the order of play does not depend on who created the
// lobby or who joined first. The draw comes from the game's seed, so it is the same every time the game is replayed. The caller puts the players in a
// fixed order first (their ids), so that one seed gives the same seating to the same players whatever the order in which they joined.
export function shuffledSeats<T>(seats: readonly T[], seed: number): T[] {
  let a = (seed ^ 0x9e3779b9) >>> 0;
  const next = (): number => {
    // mulberry32
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const out = [...seats];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(next() * (i + 1));
    [out[i], out[j]] = [out[j] as T, out[i] as T];
  }
  return out;
}
