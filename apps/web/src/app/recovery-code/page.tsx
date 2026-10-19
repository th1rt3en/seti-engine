// The recovery code of an account, shown once (after signup, after a recovery and after a new code was made). It comes in a cookie that lives for ten
// minutes; once the player says they have saved it the cookie is deleted and the code cannot be shown again (only its hash is stored).
import { RECOVERY_COOKIE } from "@/lib/session";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { recoverySavedAction } from "../actions";

export const dynamic = "force-dynamic";
export const metadata = { title: "Recovery code", robots: { index: false, follow: false } };

export default async function RecoveryCode() {
  const code = (await cookies()).get(RECOVERY_COOKIE)?.value;
  if (!code) redirect("/lobby");
  return (
    <>
      <h1>Your recovery code</h1>
      <p>
        If you forget your password, this code lets you set a new one. <b>It is shown only once</b>: write it down or keep it in a password
        manager before you continue. There is no email on this site, so without the code only the administrator can reset your password.
      </p>
      <p
        className="card"
        style={{
          fontFamily: "var(--font-mono, monospace)",
          fontSize: "1.6rem",
          letterSpacing: "0.06em",
          textAlign: "center",
          userSelect: "all",
        }}
      >
        {code}
      </p>
      <p className="muted small">
        The code works once. When you use it, you get a new one. You can make a new code at any time on your account page.
      </p>
      <form action={recoverySavedAction} className="stack">
        <button type="submit" className="primary">
          I have saved it
        </button>
      </form>
    </>
  );
}
