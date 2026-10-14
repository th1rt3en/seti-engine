import { TurnstileWidget } from "@/components/TurnstileWidget";
import { currentUser } from "@/lib/session";
import { redirect } from "next/navigation";
import { upgradeAction } from "../actions";

export default async function Account({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const user = await currentUser();
  if (user === null) redirect("/login");
  const me = user as NonNullable<typeof user>;
  const { error } = await searchParams;
  if (!me.isGuest) {
    return (
      <>
        <h1>Your account</h1>
        <p>{me.name}</p>
      </>
    );
  }
  return (
    <>
      <h1>Create an account</h1>
      <p className="muted">Your games as a guest stay with you. Rated games need an account.</p>
      {error ? <p className="error">{error}</p> : null}
      <form action={upgradeAction} className="stack">
        <label>
          Username
          <input name="name" required minLength={3} maxLength={24} pattern="[A-Za-z0-9_.\-]+" autoComplete="username" />
        </label>
        <label>
          Password (at least 8 characters)
          <input name="password" type="password" required minLength={8} autoComplete="new-password" />
        </label>
        <TurnstileWidget />
        <button type="submit">Create the account</button>
      </form>
    </>
  );
}
