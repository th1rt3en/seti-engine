// The name of a player, wherever it is written: a link to their profile, in a new tab (so that a game that is open is not left). The address is
// /players/<number> (lib/ids.ts). An AI, a guest of an old game and anybody without a number are plain text.
import type { CSSProperties, ReactNode } from "react";

export const profilePath = (num: number): string => `/players/${num}`;

export function PlayerLink({
  num,
  name,
  className,
  style,
  children,
}: { num: number | null | undefined; name: string; className?: string; style?: CSSProperties; children?: ReactNode }) {
  if (!num)
    return (
      <span className={className} style={style}>
        {children ?? name}
      </span>
    );
  return (
    <a
      href={profilePath(num)}
      target="_blank"
      rel="noopener noreferrer"
      className={className}
      style={style}
      title={`The profile of ${name} (a new tab)`}
    >
      {children ?? name}
    </a>
  );
}

/** The names of the seats of a game one after the other ("A vs B"), each a link to the profile. */
export function PlayerNames({ seats, separator = " vs " }: { seats: { name: string; num: number | null }[]; separator?: string }) {
  return (
    <>
      {seats.map((s, i) => (
        <span key={`${i}-${s.name}`}>
          {i > 0 ? separator : ""}
          <PlayerLink num={s.num} name={s.name} />
        </span>
      ))}
    </>
  );
}
