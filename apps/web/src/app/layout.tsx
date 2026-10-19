import { SettingsSync } from "@/components/SettingsSync";
import assets from "@/generated/assets.json";
import { currentUser } from "@/lib/session";
import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import { logoutAction } from "./actions";
import "./game.css";
import "./globals.css";
import "./ui.css";

export const metadata: Metadata = {
  title: "SETI online",
  description: "A fan-made, non-commercial online version of the board game SETI. Not affiliated with Czech Games Edition.",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const user = await currentUser();
  return (
    <html lang="en">
      <body
        style={{
          backgroundImage: `linear-gradient(rgba(5, 8, 18, 0.62), rgba(5, 8, 18, 0.72)), url(${assets.background})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundAttachment: "fixed",
        }}
      >
        <header className="bar">
          <Link href="/" className="brand">
            SETI online
          </Link>
          <nav>
            <Link href="/lobby">Lobby</Link>
            <Link href="/watch">Watch</Link>
            <Link href="/leaderboard">Leaderboard</Link>
            <Link href="/cards">Cards</Link>
            <Link href="/learn">How to play</Link>
            <Link href="/rules">Rules</Link>
            <Link href="/players">Players</Link>
            {user ? (
              <>
                <Link href={`/players/${user.id}`}>{user.name}</Link>
                <Link href="/account">{user.isGuest ? "Create an account" : "Account"}</Link>
                <form action={logoutAction}>
                  <button type="submit" className="link">
                    Log out
                  </button>
                </form>
              </>
            ) : (
              <>
                <Link href="/login">Log in</Link>
                <Link href="/signup">Sign up</Link>
              </>
            )}
          </nav>
        </header>
        {user ? <SettingsSync /> : null}
        <main>{children}</main>
        <footer className="foot">
          <p>
            This is an unofficial, fan-made, non-commercial project. It is not affiliated with, endorsed by or sponsored by Czech Games
            Edition (CGE). SETI: Search for Extraterrestrial Intelligence and its artwork, names and rules belong to their respective
            owners. If CGE asks us to take the project down or remove content, we will do so promptly. Takedown contact:{" "}
            <a href="mailto:seti.web.tobiko11@gmail.com">seti.web.tobiko11@gmail.com</a>.
          </p>
        </footer>
      </body>
    </html>
  );
}
