// The administrator's page (no link leads here: the address is typed). It asks for the passphrase, and then manages the accounts and the open games.
import { InlineForm } from "@/components/AdminInline";
import { ConfirmSubmit } from "@/components/ConfirmSubmit";
import { Pager } from "@/components/Pager";
import { PlayerNames } from "@/components/PlayerLink";
import { isAdmin } from "@/lib/admin";
import { countAccounts, countOpenGames, listAccounts, openGames } from "@/lib/adminData";
import { loadConfig } from "@/lib/config";
import { getDb } from "@/lib/db";
import { botVersions } from "@/lib/queries";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  adminLoginAction,
  adminLogoutAction,
  cancelGameAction,
  cancelStaleAction,
  deleteAccountAction,
  resetRatingAction,
  seedLookupAction,
  setBotEnabledAction,
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
  const models = (await botVersions(db)).filter((v) => v.approved);
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
          AI models <span className="count">{models.length}</span>
        </h2>
        <p className="muted small">
          An enabled model can be added to a game by its host. A disabled one is hidden from the lobby and cannot be added; games that
          already have it go on.
        </p>
        {models.length === 0 ? <p className="card muted empty">No model is approved yet.</p> : null}
        <div className="gamelist">
          {models.map((m) => (
            <InlineForm
              key={m.version}
              action={setBotEnabledAction}
              refresh
              className="card"
              style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", justifyContent: "space-between" }}
            >
              <input type="hidden" name="version" value={m.version} />
              <input type="hidden" name="enable" value={m.live ? "0" : "1"} />
              <span>
                <strong>{m.version}</strong> <span className={m.live ? "pill win" : "pill"}>{m.live ? "enabled" : "disabled"}</span>
                <span className="muted small"> · {m.created.slice(0, 10)}</span>
              </span>
              <button type="submit" className={m.live ? "secondary small" : "primary small"}>
                {m.live ? "Disable" : "Enable"}
              </button>
            </InlineForm>
          ))}
        </div>
      </section>

      <section className="open">
        <h2>The seed of a table</h2>
        <p className="muted small">
          The seed and the log give every hidden card of the game, so keep it to yourself while the game is played. A finished game's seed
          is public in its replay.
        </p>
        <InlineForm action={seedLookupAction} className="card" style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "end" }}>
          <label>
            Table number
            <input type="text" name="table" inputMode="numeric" placeholder="225" required style={{ width: 140 }} autoComplete="off" />
          </label>
          <button type="submit" className="secondary">
            Show the seed
          </button>
        </InlineForm>
      </section>

      <section className="open">
        <h2>
          Lobbies and games in progress <span className="count">{gameTotal}</span>
        </h2>
        <p className="muted small">Cancelling a game ends it for everybody. Nobody wins or loses, and no rating changes, rated or not.</p>
        <InlineForm
          action={cancelStaleAction}
          refresh
          ask="Cancel all the games that have had no move for that long?"
          className="card"
          style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "end" }}
        >
          <label>
            Cancel every game with no move for
            <input type="number" name="amount" min={1} defaultValue={24} style={{ width: 90 }} required />
          </label>
          <select name="unit" defaultValue="hours" aria-label="Unit">
            <option value="hours">hours</option>
            <option value="days">days</option>
          </select>
          <button type="submit" className="primary">
            Cancel them
          </button>
        </InlineForm>
        {games.length === 0 ? <p className="card muted empty">No lobby and no game in progress.</p> : null}
        <div className="gamelist">
          {games.map((g) => (
            <article className="card game" key={g.id}>
              <div className="gamehead">
                <strong>{g.seats.length > 0 ? <PlayerNames seats={g.seats} /> : `Game ${g.num ?? g.id.slice(0, 8)}`}</strong>
                <span className="badges">
                  <span className="pill">{g.status}</span>
                  {g.rated ? <span className="pill rated">rated</span> : <span className="pill">casual</span>}
                </span>
              </div>
              <p className="muted small">
                game {g.num ?? "?"} · {g.id.slice(0, 12)} · created {when(g.created_at)}
                {g.started_at ? ` · started ${when(g.started_at)}` : ""}
              </p>
              <form action={cancelGameAction} className="actions">
                <input type="hidden" name="back" value={back} />
                <input type="hidden" name="game" value={g.id} />
                <ConfirmSubmit ask="Cancel this game for everybody? No rating changes." className="btn danger small">
                  Cancel
                </ConfirmSubmit>
                <Link href={`/games/${g.num ?? g.id}`} className="btn small ghost">
                  Open
                </Link>
              </form>
            </article>
          ))}
        </div>
        <Pager
          page={Math.min(gamePage, gamePages)}
          pages={gamePages}
          link={(p) => here(accountPage, p)}
          labels={["← Previous", "Next →"]}
        />
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
        <Pager
          page={Math.min(accountPage, accountPages)}
          pages={accountPages}
          link={(p) => here(p, gamePage)}
          labels={["← Previous", "Next →"]}
        />
      </section>
    </>
  );
}
