"use client";
// A form of filters that is a GET form (it works without script) but, with script, opens the new address without leaving the place on the page.
import { useRouter } from "next/navigation";
import { type CSSProperties, type FormEvent, type ReactNode, useTransition } from "react";

export function FilterForm({
  action,
  className,
  style,
  children,
}: { action: string; className?: string; style?: CSSProperties; children: ReactNode }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const q = new URLSearchParams();
    for (const [k, v] of new FormData(e.currentTarget).entries()) if (typeof v === "string" && v !== "") q.append(k, v);
    const s = q.toString();
    start(() => router.push(s === "" ? action : `${action}?${s}`, { scroll: false }));
  };
  return (
    <form method="get" action={action} className={className} style={style} onSubmit={submit} aria-busy={pending}>
      {children}
      {pending ? <span className="spinner" role="status" aria-label="Loading" /> : null}
    </form>
  );
}
