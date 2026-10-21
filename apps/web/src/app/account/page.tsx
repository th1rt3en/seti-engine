import { TurnstileWidget } from "@/components/TurnstileWidget";
import { currentUser } from "@/lib/session";
import { redirect } from "next/navigation";
import { changePasswordAction, newRecoveryCodeAction, upgradeAction } from "../actions";

export default async function Account({ searchParams }: { searchParams: Promise<{ error?: string; notice?: string }> }) {
  const user = await currentUser();
  if (user === null) redirect("/login");
  const me = user as NonNullable<typeof user>;
  const { error, notice } = await searchParams;
  if (!me.isGuest) {
    return (
      <>
        <h1>Your account</h1>
        <p>{me.name}</p>
        {notice ? <p className="card">{notice}</p> : null}
        {error ? <p className="error">{error}</p> : null}
        <h2>Change your password</h2>
        <form action={changePasswordAction} className="stack">
          <label>
            Current password
            <input name="current" type="password" required autoComplete="current-password" />
          </label>
          <label>
            New password (at least 8 characters)
            <input name="password" type="password" required minLength={8} autoComplete="new-password" />
          </label>
          <label>
            New password again
            <input name="again" type="password" required minLength={8} autoComplete="new-password" />
          </label>
          <button type="submit" className="primary">
            Change the password
          </button>
        </form>
        <h2>Recovery code</h2>
        <p className="muted">
          The code lets you set a new password if you forget it. Only its hash is stored, so it cannot be shown again. If you have lost it,
          or your account is older than the codes, make a new one (the old one stops working).
        </p>
        <form action={newRecoveryCodeAction} className="stack">
          <label>
            Your password
            <input name="password" type="password" required autoComplete="current-password" />
          </label>
          <button type="submit" className="secondary">
            Make a new recovery code
          </button>
        </form>
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
        <button type="submit" className="primary">
          Create the account
        </button>
      </form>
    </>
  );
}
