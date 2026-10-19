// The administrator's page (no link leads here: the address is typed). It asks for the passphrase, and then manages the accounts and the open games.
import { ConfirmSubmit } from "@/components/ConfirmSubmit";
import { isAdmin } from "@/lib/admin";
import { countAccounts, countOpenGames, listAccounts, openGames } from "@/lib/adminData";
import { loadConfig } from "@/lib/config";
import { getDb } from "@/lib/db";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  adminLoginAction,
  adminLogoutAction,
  cancelGameAction,
  cancelStaleAction,
  deleteAccountAction,
  resetRatingAction,
  setPasswordAction,
  setRatingAction,
} from "./actions";

export const dynamic = "force-dynamic";
export const metadata = { title: "Admin", robots: { index: false, follow: false } };

const PAGE = 20;

const pageOf = (v: string | undefined): number => {
  const n = Number.parseInt(v ?? "1", 10);
  return Number.isFinite(n) && n >= 1 ? n : 1;
};

const when = (ms: number | null): string => (ms === null ? "" : new Date(ms).toISOString().slice(0, 16).replace("T", " "));

function Pager({ page, pages, link }: { page: number; pages: number; link: (p: number) => string }) {
  if (pages <= 1) return null;
  return (
    <nav className="pager" aria-label="Pages">
      {page > 1 ? (
        <Link href={link(page - 1)} className="btn small ghost">
          ← Previous
        </Link>
      ) : (
        <span />
      )}
      <span className="muted small">
        Page {page} of {pages}
      </span>
      {page < pages ? (
        <Link href={link(page + 1)} className="btn small ghost">
          Next →
        </Link>
      ) : (
        <span />
      )}
    </nav>
  );
}

export default async function Admin({
  searchParams,
}: { searchParams: Promise<{ q?: string; a?: string; g?: string; notice?: string; error?: string }> }) {
  if (loadConfig().adminPassphraseHash === "") notFound(); // not set up: the page does not exist
  const sp = await searchParams;
  if (!(await isAdmin())) {
    return (
      <>
        <h1>Admin</h1>
        {sp.error ? <p className="error">{sp.error}</p> : null}
        <form action={adminLoginAction} className="card" style={{ display: "grid", gap: 10, maxWidth: 420 }}>
          <label>
            Passphrase
            <input type="password" name="passphrase" autoComplete="off" required />
          </label>
          <button type="submit" className="primary">
            Enter
          </button>
        </form>
      </>
    );
  }
  const db = getDb();
  const q = (sp.q ?? "").trim();
  const accountPage = pageOf(sp.a);
  const gamePage = pageOf(sp.g);
  const [accountTotal, gameTotal] = await Promise.all([countAccounts(db, q), countOpenGames(db)]);
  const accountPages = Math.max(1, Math.ceil(accountTotal / PAGE));
  const gamePages = Math.max(1, Math.ceil(gameTotal / PAGE));
  const [accounts, games] = await Promise.all([
    listAccounts(db, q, PAGE, (Math.min(accountPage, accountPages) - 1) * PAGE),
    openGames(db, PAGE, (Math.min(gamePage, gamePages) - 1) * PAGE),
  ]);
  const here = (a: number, g: number): string => {
    const p = new URLSearchParams();
    if (q) p.set("q", q);
    if (a > 1) p.set("a", String(a));
    if (g > 1) p.set("g", String(g));
    const t = p.toString();
    return t ? `/admin?${t}` : "/admin";
  };
  const back = here(accountPage, gamePage);
  return (
    <>
      <header className="pagehead" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <h1>Admin</h1>
        <form action={adminLogoutAction}>
          <button type="submit" className="secondary small">
            Log out
          </button>
        </form>
      </header>
      {sp.notice ? <p className="card">{sp.notice}</p> : null}
      {sp.error ? <p className="error">{sp.error}</p> : null}

      <section className="open">
        <h2>
          Lobbies and games in progress <span className="count">{gameTotal}</span>
        </h2>
        <p className="muted small">Cancelling a game ends it for everybody. Nobody wins or loses, and no rating changes, rated or not.</p>
        <form action={cancelStaleAction} className="card" style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "end" }}>
          <input type="hidden" name="back" value={back} />
          <label>
            Cancel every game with no move for
            <input type="number" name="amount" min={1} defaultValue={24} style={{ width: 90 }} required />
          </label>
          <select name="unit" defaultValue="hours" aria-label="Unit">
            <option value="hours">hours</option>
            <option value="days">days</option>
          </select>
          <ConfirmSubmit ask="Cancel all the games that have had no move for that long?" className="primary">
            Cancel them
          </ConfirmSubmit>
        </form>
        {games.length === 0 ? <p className="card muted empty">No lobby and no game in progress.</p> : null}
        <div className="gamelist">
          {games.map((g) => (
            <article className="card game" key={g.id}>
              <div className="gamehead">
                <strong>{g.seats.length > 0 ? g.seats.join(" vs ") : `Game ${g.id.slice(0, 8)}`}</strong>
                <span className="badges">
                  <span className="pill">{g.status}</span>
                  {g.rated ? <span className="pill rated">rated</span> : <span className="pill">casual</span>}
                </span>
              </div>
              <p className="muted small">
                {g.id.slice(0, 12)} · created {when(g.created_at)}
                {g.started_at ? ` · started ${when(g.started_at)}` : ""}
              </p>
              <form action={cancelGameAction} className="actions">
                <input type="hidden" name="back" value={back} />
                <input type="hidden" name="game" value={g.id} />
                <ConfirmSubmit ask="Cancel this game for everybody? No rating changes." className="btn small">
                  Cancel
                </ConfirmSubmit>
                <Link href={`/games/${g.id}`} className="btn small ghost">
                  Open
                </Link>
              </form>
            </article>
          ))}
        </div>
        <Pager page={Math.min(gamePage, gamePages)} pages={gamePages} link={(p) => here(accountPage, p)} />
      </section>

      <section className="open">
        <h2>
          Accounts <span className="count">{accountTotal}</span>
        </h2>
        <form method="get" action="/admin" className="card" style={{ display: "flex", gap: 8 }}>
          <input type="search" name="q" defaultValue={q} placeholder="Find a name" aria-label="Find a name" />
          <button type="submit" className="secondary">
            Find
          </button>
        </form>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Rating</th>
                <th>Set the rating</th>
                <th>Set the password</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {accounts.map((u) => (
                <tr key={u.id}>
                  <td>
                    {u.name} {u.is_guest ? <span className="pill">guest</span> : null}
                    {u.open_games > 0 ? <span className="pill">in a game</span> : null}
                    <div className="muted small">joined {when(u.created_at)}</div>
                  </td>
                  <td>{u.rating ?? "unrated (0)"}</td>
                  <td>
                    <form action={setRatingAction} style={{ display: "flex", gap: 6 }}>
                      <input type="hidden" name="back" value={back} />
                      <input type="hidden" name="user" value={u.id} />
                      <input type="hidden" name="name" value={u.name} />
                      <input
                        type="number"
                        name="rating"
                        min={0}
                        max={4000}
                        defaultValue={u.rating ?? 0}
                        style={{ width: 90 }}
                        aria-label={`Rating of ${u.name}`}
                      />
                      <button type="submit" className="secondary small">
                        Set
                      </button>
                    </form>
                  </td>
                  <td>
                    {u.is_guest ? (
                      <span className="muted small">guest</span>
                    ) : (
                      <form action={setPasswordAction} style={{ display: "flex", gap: 6 }}>
                        <input type="hidden" name="back" value={back} />
                        <input type="hidden" name="user" value={u.id} />
                        <input type="hidden" name="name" value={u.name} />
                        <input
                          type="text"
                          name="password"
                          minLength={8}
                          maxLength={200}
                          required
                          autoComplete="off"
                          placeholder="new password"
                          style={{ width: 150 }}
                          aria-label={`New password of ${u.name}`}
                        />
                        <ConfirmSubmit ask={`Set a new password for ${u.name}? Their sessions end.`} className="secondary small">
                          Set
                        </ConfirmSubmit>
                      </form>
                    )}
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      <form action={resetRatingAction}>
                        <input type="hidden" name="back" value={back} />
                        <input type="hidden" name="user" value={u.id} />
                        <input type="hidden" name="name" value={u.name} />
                        <ConfirmSubmit ask={`Reset the rating of ${u.name} to the start (0, unrated)?`} className="secondary small">
                          Reset
                        </ConfirmSubmit>
                      </form>
                      <form action={deleteAccountAction}>
                        <input type="hidden" name="back" value={back} />
                        <input type="hidden" name="user" value={u.id} />
                        <input type="hidden" name="name" value={u.name} />
                        <ConfirmSubmit ask={`Delete the account ${u.name}? This cannot be undone.`} className="secondary small">
                          Delete
                        </ConfirmSubmit>
                      </form>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pager page={Math.min(accountPage, accountPages)} pages={accountPages} link={(p) => here(p, gamePage)} />
      </section>
    </>
  );
}
