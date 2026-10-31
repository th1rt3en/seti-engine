"use client";
// The invitations to a lobby, as a notice at the bottom right corner of every page for a signed-in player. The site asks for them every few seconds
// while the page is in view. Accepting takes the player to the lobby at once; declining tells the host (the seat shows the refusal).
import { answerInviteAction } from "@/app/actions";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

interface Invite {
  gameId: string;
  num: number | null;
  seat: number;
  host: string;
  at: number;
}

const POLL_MS = 10_000;

export function InviteToasts() {
  const router = useRouter();
  const [invites, setInvites] = useState<Invite[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const answered = useRef(new Set<string>());

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/invites", { cache: "no-store" });
      if (!res.ok) return setInvites([]);
      const body = (await res.json()) as { invites: Invite[] };
      setInvites(body.invites.filter((i) => !answered.current.has(i.gameId)));
    } catch {
      // offline: the next poll tries again
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, POLL_MS);
    const onShow = () => {
      if (document.visibilityState === "visible") void load();
    };
    document.addEventListener("visibilitychange", onShow);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onShow);
    };
  }, [load]);

  const answer = async (i: Invite, accept: boolean) => {
    setBusy(i.gameId);
    setError("");
    const res = await answerInviteAction(i.gameId, accept);
    setBusy(null);
    answered.current.add(i.gameId);
    setInvites((all) => all.filter((x) => x.gameId !== i.gameId));
    if (!res.ok) setError(res.message);
    else if (accept && res.path) router.push(res.path);
  };

  if (invites.length === 0 && error === "") return null;
  return (
    <div className="invitetoasts" aria-live="polite">
      {invites.map((i) => (
        <section key={i.gameId} className="invitetoast" aria-label="Invitation to a game">
          <p>
            <strong>{i.host || "A player"}</strong> invited you to a game{i.num === null ? "" : ` (#${i.num})`}.
          </p>
          <div className="inviteanswer">
            <button type="button" className="primary" disabled={busy === i.gameId} onClick={() => void answer(i, true)}>
              Accept
            </button>
            <button type="button" className="secondary" disabled={busy === i.gameId} onClick={() => void answer(i, false)}>
              Decline
            </button>
          </div>
        </section>
      ))}
      {error !== "" ? (
        <section className="invitetoast" role="alert">
          <p>{error}</p>
          <div className="inviteanswer">
            <button type="button" className="secondary" onClick={() => setError("")}>
              Close
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
