"use client";
// A link of a pager: while the page that it leads to is being made, a small spinner turns in it (the hook needs a client component).
import Link, { useLinkStatus } from "next/link";

function Pending() {
  const { pending } = useLinkStatus();
  return pending ? <span className="spinner" role="status" aria-label="Loading the page" /> : null;
}

export function PagerLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className="btn small ghost">
      {label}
      <Pending />
    </Link>
  );
}
