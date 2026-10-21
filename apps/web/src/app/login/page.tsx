import { TurnstileWidget } from "@/components/TurnstileWidget";
import Link from "next/link";
import { loginAction } from "../actions";

export default async function Login({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  return (
    <>
      <h1>Log in</h1>
      {error ? <p className="error">{error}</p> : null}
      <form action={loginAction} className="stack">
        <label>
          Username
          <input name="name" required autoComplete="username" />
        </label>
        <label>
          Password
          <input name="password" type="password" required autoComplete="current-password" />
        </label>
        <TurnstileWidget />
        <button type="submit" className="primary">
          Log in
        </button>
      </form>
      <p className="muted small">
        <Link href="/recover">Forgot your password?</Link>
      </p>
    </>
  );
}
