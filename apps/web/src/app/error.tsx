"use client";
// What the player sees when a page fails: a plain message and a way back, not a blank page. The error itself is stored as an object in the bucket
// (instrumentation.ts), so nothing of it is shown here.
import Link from "next/link";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <>
      <h1>Something went wrong</h1>
      <p>The page could not be shown. The error has been recorded. You can try again, or go back to the lobby.</p>
      <p>
        <button type="button" onClick={() => reset()}>
          Try again
        </button>{" "}
        <Link href="/lobby">Back to the lobby</Link>
      </p>
    </>
  );
}
