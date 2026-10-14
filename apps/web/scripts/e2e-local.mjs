// A local end-to-end check of the whole backend: two players play through the Worker (wrangler dev) and the engine service.
// Start the engine (port 8765) and `wrangler dev --local --port 8787` first (apps/worker/.dev.vars holds the matching public key),
// put the private key in .local-priv.pem at the repo root, then run:  node apps/web/scripts/e2e-local.mjs [actions]
import { readFileSync } from "node:fs";
import { SignJWT, importPKCS8 } from "jose";

const WORKER = process.env.WORKER_URL ?? "http://127.0.0.1:8787";
const WS = WORKER.replace("http", "ws");
const key = await importPKCS8(readFileSync(new URL("../../../.local-priv.pem", import.meta.url), "utf8"), "ES256");
const token = (sub, name) =>
  new SignJWT({ name, reg: true })
    .setProtectedHeader({ alg: "ES256" })
    .setIssuer("http://localhost:3000")
    .setAudience("seti-worker")
    .setSubject(sub)
    .setExpirationTime("5m")
    .sign(key);
const maxActions = Number(process.argv[2] ?? 150);

async function api(tok, path, method = "GET", body = undefined) {
  const res = await fetch(`${WORKER}${path}`, {
    method,
    headers: { authorization: `Bearer ${tok}`, "content-type": "application/json" },
    body: body && JSON.stringify(body),
  });
  return res.json();
}

const alice = await token("e2e-alice", "Alice");
const bob = await token("e2e-bob", "Bob");
const created = await api(alice, "/games", "POST", { options: { players: 2 }, clock: { kind: "none" }, rated: true });
if (!created.ok) throw new Error(`create failed: ${JSON.stringify(created)}`);
const id = created.id;
console.log("game", id);
console.log("join", JSON.stringify(await api(bob, `/games/${id}/join`, "POST")));

const sockets = [alice, bob].map((t, seat) => {
  const ws = new WebSocket(`${WS}/games/${id}/ws?token=${t}`);
  const s = { ws, seat, view: null, last: null, errors: [] };
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.t === "view") s.view = m;
    if (m.t === "error") s.errors.push(m);
    if (m.t === "ended") s.ended = m.result;
    s.last = m;
  };
  return s;
});
const until = async (f, ms = 15000) => {
  const t0 = Date.now();
  while (!f()) {
    if (Date.now() - t0 > ms) throw new Error("timeout waiting");
    await new Promise((r) => setTimeout(r, 20));
  }
};
await until(() => sockets.every((s) => s.view !== null));
console.log("both connected; status", sockets[0].view.status);

let n = 0;
let seed = 11;
while (n < maxActions && !sockets[0].ended) {
  const actor = sockets.find((s) => s.view.view.legal.length > 0);
  if (!actor) throw new Error("nobody can act");
  const legal = actor.view.view.legal;
  seed = (seed * 1103515245 + 12345) & 0x7fffffff;
  const before = actor.view.seq;
  actor.ws.send(JSON.stringify({ t: "action", seq: before, action: legal[seed % legal.length] }));
  await until(() => sockets.every((s) => s.view.seq > before || s.ended));
  n++;
}
console.log("played", n, "actions; errors:", sockets.flatMap((s) => s.errors).length);
const spectator = new WebSocket(`${WS}/games/${id}/ws`);
let spec = null;
spectator.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.t === "view") spec = m;
};
await until(() => spec !== null);
console.log(
  "spectator sees viewer =",
  spec.view.viewer,
  "legal =",
  spec.view.legal.length,
  "hands hidden =",
  spec.view.state.players.every((p) => p.hand.every((c) => c === "?")),
);

// a wrong-turn action is refused
const idle = sockets.find((s) => s.view.view.legal.length === 0);
if (idle && !sockets[0].ended) {
  idle.ws.send(JSON.stringify({ t: "action", seq: idle.view.seq, action: { type: "pass" } }));
  await until(() => idle.errors.length > 0);
  console.log("wrong-turn action refused:", idle.errors.at(-1).code);
}

if (!sockets[0].ended) {
  sockets[1].ws.send(JSON.stringify({ t: "resign" }));
  await until(() => sockets[0].ended);
}
console.log("ended:", JSON.stringify(sockets[0].ended.reason), "winners", sockets[0].ended.winners);
const meta = await fetch(`${WORKER}/games/${id}`).then((r) => r.json());
const log = await fetch(`${WORKER}/games/${id}/log`).then((r) => r.json());
console.log("meta status", meta.status, "log length", log.length);
for (const s of sockets) s.ws.close();
spectator.close();
console.log("GAME_ID", id);
