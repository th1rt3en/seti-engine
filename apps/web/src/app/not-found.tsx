import Link from "next/link";

export default function NotFound() {
  return (
    <>
      <h1>This page does not exist</h1>
      <p>The address may be wrong, or the game was deleted (a table that everybody left is removed).</p>
      <p>
        <Link href="/lobby">Back to the lobby</Link>
      </p>
    </>
  );
}
