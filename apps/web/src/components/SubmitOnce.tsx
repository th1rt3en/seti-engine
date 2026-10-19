"use client";
// A submit button that can be pressed once: from the first press it stays disabled (a second press would send the form again, and for the button that
// creates a game, make a second game). The page changes at once when the action succeeds; if it fails, the page comes back with a message.
import { useEffect, useState } from "react";
import { useFormStatus } from "react-dom";

export function SubmitOnce({ children, className, busy = "Working..." }: { children: React.ReactNode; className?: string; busy?: string }) {
  const { pending } = useFormStatus();
  const [sent, setSent] = useState(false);
  useEffect(() => {
    if (pending) setSent(true);
  }, [pending]);
  return (
    <button type="submit" className={className} disabled={pending || sent} aria-busy={pending || sent}>
      {pending || sent ? busy : children}
    </button>
  );
}
