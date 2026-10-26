"use client";
// A form of filters that is a GET form (it works without script) but, with script, applies every choice at once and opens the new address without
// leaving the place on the page: a choice in a list, a switch or a box applies when it is made, a text when the visitor stops typing. The button of
// the form is only for a browser without script.
import { useRouter } from "next/navigation";
import { type CSSProperties, type ChangeEvent, type FormEvent, type ReactNode, useEffect, useRef, useTransition } from "react";

const TYPING_MS = 400;

export function FilterForm({
  action,
  className,
  style,
  children,
}: { action: string; className?: string; style?: CSSProperties; children: ReactNode }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => (timer.current === null ? undefined : clearTimeout(timer.current)), []);
  const open = (form: HTMLFormElement) => {
    const q = new URLSearchParams();
    for (const [k, v] of new FormData(form).entries()) if (typeof v === "string" && v !== "") q.append(k, v);
    const s = q.toString();
    start(() => router.push(s === "" ? action : `${action}?${s}`, { scroll: false }));
  };
  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    open(e.currentTarget);
  };
  const change = (e: ChangeEvent<HTMLFormElement>) => {
    const form = e.currentTarget;
    if (timer.current !== null) clearTimeout(timer.current);
    const typing = e.target instanceof HTMLInputElement && (e.target.type === "search" || e.target.type === "text");
    if (typing) timer.current = setTimeout(() => open(form), TYPING_MS);
    else open(form);
  };
  return (
    <form method="get" action={action} className={className} style={style} onSubmit={submit} onChange={change} aria-busy={pending}>
      {children}
      {pending ? <span className="spinner" role="status" aria-label="Loading" /> : null}
    </form>
  );
}
