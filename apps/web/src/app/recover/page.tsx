import { TurnstileWidget } from "@/components/TurnstileWidget";
import Link from "next/link";
import { recoverAction } from "../actions";

export const metadata = { title: "Forgot your password", robots: { index: false, follow: false } };

export default async function Recover({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  return (
    <>
      <h1>Forgot your password</h1>
      <p className="muted">
        Enter your username, the recovery code you were given when you made the account, and a new password. If you have lost the code too,
        ask the administrator to reset your password.
      </p>
      {error ? <p className="error">{error}</p> : null}
      <form action={recoverAction} className="stack">
        <label>
          Username
          <input name="name" required autoComplete="username" />
        </label>
        <label>
          Recovery code
          <input
            name="code"
            required
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            placeholder="XXXXX-XXXXX-XXXXX-XXXXX"
          />
        </label>
        <label>
          New password (at least 8 characters)
          <input name="password" type="password" required minLength={8} autoComplete="new-password" />
        </label>
        <TurnstileWidget />
        <button type="submit" className="primary">
          Set the new password
        </button>
      </form>
      <p className="muted small">
        <Link href="/login">Back to log in</Link>
      </p>
    </>
  );
}
