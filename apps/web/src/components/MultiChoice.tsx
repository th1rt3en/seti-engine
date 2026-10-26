"use client";
// A filter with several choices that all count (a game with any of the chosen species, a player who picked any of the chosen organizations): each choice is
// a button that is switched on or off, and the page changes at once. The address keeps the choices as `name=a,b`, next to the other filters (`base`).
import { useRouter } from "next/navigation";
import { useTransition } from "react";

export function MultiChoice({
  name,
  label,
  choices,
  selected,
  base,
  action,
}: {
  name: string;
  label: string;
  choices: { value: string; label: string }[];
  selected: string[];
  /** The other filters, as they are in the address. */
  base: Record<string, string>;
  action: string;
}) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const toggle = (value: string) => {
    const next = selected.includes(value) ? selected.filter((x) => x !== value) : [...selected, value];
    const q = new URLSearchParams(base);
    if (next.length > 0) q.set(name, next.join(","));
    else q.delete(name);
    const s = q.toString();
    start(() => router.push(s === "" ? action : `${action}?${s}`, { scroll: false }));
  };
  return (
    <fieldset className="multichoice" aria-busy={pending}>
      <legend className="stat-filter-name">
        {label}
        {pending ? <span className="spinner" role="status" aria-label="Loading" /> : null}
      </legend>
      <div className="fpills">
        {choices.map((c) => (
          <button
            key={c.value}
            type="button"
            className={selected.includes(c.value) ? "fpill on" : "fpill"}
            aria-pressed={selected.includes(c.value)}
            onClick={() => toggle(c.value)}
          >
            {c.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
