"use client";
// Keeps the settings of the game page with the account: when a signed-in player opens a page the saved settings are applied to this browser (or, if
// nothing is saved yet, this browser's settings are saved), and a change made here is saved a moment later. Without an account nothing happens.
import { useEffect } from "react";

const KEYS = ["seti-turn-sound", "seti-confirm-irreversible", "seti-turn-notify", "seti-animations", "seti-hand-scale"];
const EVENT = "seti-settings";

function local(): Record<string, string> {
  const out: Record<string, string> = {};
  try {
    for (const k of KEYS) {
      const v = localStorage.getItem(k);
      if (v !== null) out[k] = v;
    }
  } catch {
    // no storage
  }
  return out;
}

export function SettingsSync() {
  useEffect(() => {
    let applying = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const push = () => {
      fetch("/api/settings", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ settings: local() }),
      }).catch(() => {});
    };
    const onChange = () => {
      if (applying) return;
      if (timer !== null) clearTimeout(timer);
      timer = setTimeout(push, 800);
    };
    fetch("/api/settings")
      .then(async (res) => {
        if (!res.ok) return;
        const saved = ((await res.json()) as { settings: Record<string, string> }).settings;
        if (Object.keys(saved).length === 0) {
          if (Object.keys(local()).length > 0) push();
          return;
        }
        applying = true;
        try {
          for (const [k, v] of Object.entries(saved)) localStorage.setItem(k, v);
        } catch {
          // no storage
        }
        window.dispatchEvent(new Event(EVENT));
        applying = false;
      })
      .catch(() => {});
    window.addEventListener(EVENT, onChange);
    return () => {
      window.removeEventListener(EVENT, onChange);
      if (timer !== null) clearTimeout(timer);
    };
  }, []);
  return null;
}
