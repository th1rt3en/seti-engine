"use client";
// The Cloudflare Turnstile challenge of a form, rendered from the client. The answer goes into a hidden field that React controls, so a
// hydration pass cannot wipe it (it did when the script's own markup was part of the server-rendered form).
import { useEffect, useRef, useState } from "react";

interface TurnstileApi {
  render(el: HTMLElement, options: Record<string, unknown>): string;
  remove(id: string): void;
}

declare global {
  interface Window {
    turnstile?: TurnstileApi;
  }
}

const SCRIPT = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

export function TurnstileField({ siteKey }: { siteKey: string }) {
  const box = useRef<HTMLDivElement>(null);
  const [token, setToken] = useState("");

  useEffect(() => {
    let id: string | undefined;
    let cancelled = false;
    const mount = () => {
      if (cancelled || !box.current || !window.turnstile) return;
      id = window.turnstile.render(box.current, {
        sitekey: siteKey,
        callback: (t: string) => setToken(t),
        "expired-callback": () => setToken(""),
        "error-callback": () => setToken(""),
      });
    };
    if (window.turnstile) mount();
    else {
      let script = document.querySelector<HTMLScriptElement>("script[data-turnstile]");
      if (!script) {
        script = document.createElement("script");
        script.src = SCRIPT;
        script.async = true;
        script.dataset.turnstile = "1";
        document.head.appendChild(script);
      }
      script.addEventListener("load", mount);
    }
    return () => {
      cancelled = true;
      if (id !== undefined && window.turnstile) window.turnstile.remove(id);
    };
  }, [siteKey]);

  return (
    <>
      <div ref={box} />
      <p className="small muted" aria-live="polite">
        {token === "" ? "Security check: waiting for it to finish..." : "Security check: passed."}
      </p>
      <input type="hidden" name="cf-turnstile-response" value={token} readOnly />
    </>
  );
}
