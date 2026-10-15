"use client";
// A line of text in which the names of cards are shown as "Name (id)", with the cards' pictures behind them: resting the pointer on a card name for a
// second shows the card enlarged beside it (a long press on a touch screen). Organization names do the same with their board (OrgName).
import { cardImage } from "@/lib/cardImages";
import { ORG_NAMES } from "@/lib/moves";
import { ZOOM_SECONDS, touchScreen, useLongPress } from "@/lib/touch";
import { Fragment, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import cards from "../generated/cards.json";
import { OrgName } from "./OrgName";

const CARDS = cards as unknown as Record<string, { name: string }>;
const RATIO = 1040 / 747;
const HOVER_DELAY_MS = 1000;
const zoomWidth = (): number => Math.round(Math.min(500, Math.max(320, window.innerWidth * 0.26)));

/** One card name: its text with the enlarged picture after a second on it. */
export function CardLink({ id, children }: { id: string; children: React.ReactNode }) {
  const [zoom, setZoom] = useState<{ x: number; y: number; w: number } | null>(null);
  const node = useRef<HTMLSpanElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancel = () => {
    if (timer.current !== null) clearTimeout(timer.current);
    timer.current = null;
    setZoom(null);
  };
  useEffect(
    () => () => {
      if (timer.current !== null) clearTimeout(timer.current);
    },
    [],
  );
  const show = () => {
    const r = node.current?.getBoundingClientRect();
    if (!r) return;
    const w = zoomWidth();
    const h = Math.round(w * RATIO);
    let x = r.right + 14;
    if (x + w > window.innerWidth - 8) x = Math.max(8, r.left - w - 14);
    const y = Math.min(Math.max(8, r.top + r.height / 2 - h / 2), Math.max(8, window.innerHeight - h - 8));
    setZoom({ x, y, w });
  };
  const longPress = useLongPress(() => {
    if (!touchScreen()) return;
    cancel();
    show();
    timer.current = setTimeout(cancel, ZOOM_SECONDS * 1000);
  });
  const src = cardImage(id);
  return (
    <>
      <span
        {...longPress}
        ref={node}
        className="cardlink"
        onMouseEnter={() => {
          if (touchScreen() || !src) return;
          cancel();
          timer.current = setTimeout(show, HOVER_DELAY_MS);
        }}
        onMouseLeave={() => !touchScreen() && cancel()}
      >
        {children}
      </span>
      {zoom && src
        ? createPortal(
            // biome-ignore lint/a11y/useKeyWithClickEvents: a zoom of a picture for touch screens; the picture is not an action
            <img
              className="cardzoom"
              src={src}
              alt=""
              width={zoom.w}
              height={Math.round(zoom.w * RATIO)}
              style={{ left: zoom.x, top: zoom.y, pointerEvents: touchScreen() ? "auto" : undefined }}
              onClick={cancel}
            />,
            document.body,
          )
        : null}
    </>
  );
}

type Ref = { start: number; end: number; kind: "card" | "org"; id: string };

/** The card names ("Name (id)") and organization names in a text. */
function refs(text: string): Ref[] {
  const out: Ref[] = [];
  for (const m of text.matchAll(/\(([^()]+)\)/g)) {
    const id = m[1] ?? "";
    const info = CARDS[id];
    if (!info) continue;
    const at = m.index ?? 0;
    const before = text.slice(0, at).trimEnd();
    if (before.endsWith(info.name)) out.push({ start: before.length - info.name.length, end: at + m[0].length, kind: "card", id });
  }
  for (const [id, name] of Object.entries(ORG_NAMES)) {
    let from = text.indexOf(name);
    while (from >= 0) {
      if (!out.some((r) => from < r.end && from + name.length > r.start))
        out.push({ start: from, end: from + name.length, kind: "org", id });
      from = text.indexOf(name, from + name.length);
    }
  }
  return out.sort((a, b) => a.start - b.start);
}

export function CardText({ text }: { text: string }) {
  const found = refs(text);
  if (found.length === 0) return <>{text}</>;
  const parts: React.ReactNode[] = [];
  let at = 0;
  for (const r of found) {
    if (r.start < at) continue;
    if (r.start > at) parts.push(<Fragment key={`t${at}`}>{text.slice(at, r.start)}</Fragment>);
    parts.push(
      r.kind === "card" ? (
        <CardLink key={`c${r.start}`} id={r.id}>
          {text.slice(r.start, r.end)}
        </CardLink>
      ) : (
        <OrgName key={`o${r.start}`} id={r.id} />
      ),
    );
    at = r.end;
  }
  if (at < text.length) parts.push(<Fragment key={`t${at}`}>{text.slice(at)}</Fragment>);
  return <>{parts}</>;
}
