"use client";
// A choice of a filter: a link that keeps the page where it is (no jump back to the top) and shows a small spinner while the new numbers are made.
import Link, { useLinkStatus } from "next/link";

function Pending() {
  const { pending } = useLinkStatus();
  return pending ? <span className="spinner" role="status" aria-label="Loading" /> : null;
}

export function FilterPill({ href, label, on }: { href: string; label: string; on: boolean }) {
  return (
    <Link href={href} scroll={false} className={on ? "fpill on" : "fpill"} aria-current={on ? "true" : undefined}>
      {label}
      <Pending />
    </Link>
  );
}
