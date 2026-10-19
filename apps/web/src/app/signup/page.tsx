import { TurnstileWidget } from "@/components/TurnstileWidget";
import { signupAction } from "../actions";

export default async function Signup({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  return (
    <>
      <h1>Sign up</h1>
      {error ? <p className="error">{error}</p> : null}
      <form action={signupAction} className="stack">
        <label>
          Username (shown to other players)
          <input name="name" required minLength={3} maxLength={24} pattern="[A-Za-z0-9_.\-]+" autoComplete="username" />
        </label>
        <label>
          Password (at least 8 characters)
          <input name="password" type="password" required minLength={8} autoComplete="new-password" />
        </label>
        <TurnstileWidget />
        <p className="muted small">
          After this you get a one-time recovery code. Keep it: it is the only way to set a new password if you forget yours.
        </p>
        <button type="submit" className="primary">Create the account</button>
      </form>
    </>
  );
}
