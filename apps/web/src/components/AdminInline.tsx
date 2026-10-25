"use client";
// Forms of the administrator's page that stay on the page: the answer shows beside the button, the address does not change, and the page does not
// jump (the lists are refreshed in place when something changed).
import { useRouter } from "next/navigation";
import { type FormEvent, type ReactNode, useState, useTransition } from "react";

type Said = { ok: boolean; message: string };

export function InlineForm({
  action,
  refresh = false,
  className,
  style,
  children,
  ask,
}: {
  action: (form: FormData) => Promise<Said>;
  /** Read the lists of the page again after the action (a count changed). */
  refresh?: boolean;
  className?: string;
  style?: React.CSSProperties;
  children: ReactNode;
  /** A question to answer yes to before the action runs. */
  ask?: string;
}) {
  const router = useRouter();
  const [said, setSaid] = useState<Said | null>(null);
  const [busy, start] = useTransition();
  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (ask && !window.confirm(ask)) return;
    const data = new FormData(e.currentTarget);
    start(async () => {
      try {
        setSaid(await action(data));
        if (refresh) router.refresh();
      } catch {
        // a failure of the action is said beside the button: it must not take the whole page down
        setSaid({ ok: false, message: "That did not work: the server could not do it. Try again, or look at the error reports." });
      }
    });
  };
  return (
    <form onSubmit={submit} className={className} style={style} aria-busy={busy}>
      {children}
      {busy ? <span className="spinner" role="status" aria-label="Working" /> : null}
      {said ? (
        <output className={said.ok ? "adminsaid" : "error"} style={{ alignSelf: "center", whiteSpace: "pre-line" }}>
          {said.message}
        </output>
      ) : null}
    </form>
  );
}
