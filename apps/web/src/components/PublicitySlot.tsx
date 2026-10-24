"use client";
// The publicity track in the right column, unless the player has turned it off in the settings (the gear in the heading of the game).
import { useGameSettings } from "@/lib/gameSettings";
import type { View } from "@seti/protocol";
import { PublicityTrack } from "./PublicityTrack";

export function PublicitySlot({ view, names }: { view: View; names: string[] }) {
  const { publicityTrack } = useGameSettings();
  return publicityTrack ? <PublicityTrack view={view} names={names} /> : null;
}
