"use client";
// The result of the move that is picked, before it is confirmed: the net change of points and resources that the engine says the move would make (it
// plays the move on a copy and reports the change of this player's numbers; nothing is stored). It says nothing about what the move would reveal.
import { useEffect } from "react";
import { Changes } from "./Reward";

/** A number made from the move, to match an answer to the question that was sent. */
export const moveKey = (move: unknown): number => {
  const text = JSON.stringify(move);
  let h = 5381;
  for (let i = 0; i < text.length; i++) h = ((h << 5) + h + text.charCodeAt(i)) | 0;
  return h >>> 0;
};

export function MovePreview({
  move,
  previews,
  send,
}: {
  move: unknown;
  previews: Record<number, Record<string, number> | null>;
  send: (msg: unknown) => void;
}) {
  const id = moveKey(move);
  // biome-ignore lint/correctness/useExhaustiveDependencies: ask once for each move that is picked
  useEffect(() => {
    if (!(id in previews)) send({ t: "preview", id, action: move });
  }, [id]);
  const changes = previews[id];
  if (!changes || Object.keys(changes).length === 0) return null;
  return (
    <span className="movepreview" title="What this move would change for you">
      {" "}
      Result: <Changes changes={changes} size={16} />
    </span>
  );
}
