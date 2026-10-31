import type { Options } from "@seti/protocol";
import { describe, expect, it } from "vitest";
import { Conn, alice, bob, cy, guest, makeRoom } from "./helpers.js";

const three = { players: 3 } as Options;
const none = { kind: "none" } as const;
const target = (who: { id: string; name: string }) => ({ id: who.id, name: who.name });

async function lobby() {
  const t = makeRoom();
  await t.room.init("g1", three, none, false, alice);
  return t;
}

describe("an invitation to a lobby", () => {
  it("holds a free seat for the invited player, who is not seated until they accept", async () => {
    const t = await lobby();
    expect(await t.room.invite(alice, 1, target(bob))).toEqual({ ok: true });
    const meta = await t.room.meta();
    expect(meta?.seats[1]).toBeNull();
    expect(meta?.invites).toMatchObject([{ seat: 1, id: bob.id, name: "Bob", status: "pending" }]);
    expect(t.sink.lobbies.at(-1)?.invites).toHaveLength(1); // the site learns of it from the sink
  });

  it("is told to the lobby: the seat shows the invited player as pending, and still counts as free", async () => {
    const t = await lobby();
    const c = new Conn("c1", alice.id);
    t.conns.push(c);
    await t.room.invite(alice, 1, target(bob));
    await t.room.connect(c);
    const m = c.last("lobby") as { seats: unknown[]; invites: unknown[]; full: boolean };
    expect(m.seats[1]).toBeNull();
    expect(m.invites[1]).toEqual({ name: "Bob", status: "pending" });
    expect(m.invites[0]).toBeNull();
    expect(m.full).toBe(false);
  });

  it("only the host invites, only to a free seat, and nobody twice", async () => {
    const t = await lobby();
    expect(await t.room.invite(bob, 1, target(cy))).toMatchObject({ ok: false, code: "not_host" });
    expect(await t.room.invite(alice, 0, target(bob))).toMatchObject({ ok: false, code: "seat_taken" });
    expect(await t.room.invite(alice, 5, target(bob))).toMatchObject({ ok: false, code: "seat_taken" });
    expect(await t.room.invite(alice, 1, target(alice))).toMatchObject({ ok: false, code: "already_seated" });
    await t.room.invite(alice, 1, target(bob));
    expect(await t.room.invite(alice, 2, target(bob))).toMatchObject({ ok: false, code: "already_invited" });
  });

  it("keeps the seat from other players who join: only a seat that nobody holds is free", async () => {
    const t = await lobby();
    await t.room.invite(alice, 1, target(bob));
    expect(await t.room.join(cy)).toMatchObject({ ok: true, seat: 2 });
    expect(await t.room.join(guest)).toMatchObject({ ok: false, code: "full" });
    expect((await t.room.meta())?.seats[1]).toBeNull();
  });

  it("is accepted: the player takes the held seat at once, and the invitation is gone", async () => {
    const t = await lobby();
    await t.room.invite(alice, 1, target(bob));
    expect(await t.room.acceptInvite(bob)).toEqual({ ok: true, seat: 1 });
    const meta = await t.room.meta();
    expect(meta?.seats[1]?.id).toBe(bob.id);
    expect(meta?.invites).toBeUndefined();
    expect(meta?.joined).toContain(bob.id);
    expect(await t.room.acceptInvite(bob)).toMatchObject({ ok: false, code: "no_invite" });
  });

  it("is declined: the seat shows the refusal, stays free, and the player cannot accept it any more", async () => {
    const t = await lobby();
    const c = new Conn("c1", alice.id);
    t.conns.push(c);
    await t.room.invite(alice, 1, target(bob));
    expect(await t.room.declineInvite(bob)).toEqual({ ok: true });
    expect(c.last("lobby")).toMatchObject({ invites: [null, { name: "Bob", status: "declined" }, null] });
    expect(await t.room.acceptInvite(bob)).toMatchObject({ ok: false, code: "no_invite" });
    // a declined invitation does not hold the seat
    expect(await t.room.join(cy)).toMatchObject({ ok: true, seat: 1 });
    expect((await t.room.meta())?.invites).toBeUndefined();
  });

  it("can be taken back by the host (a pending one or a refusal), and by nobody else", async () => {
    const t = await lobby();
    await t.room.invite(alice, 1, target(bob));
    expect(await t.room.cancelInvite(bob, 1)).toMatchObject({ ok: false, code: "not_host" });
    expect(await t.room.cancelInvite(alice, 2)).toMatchObject({ ok: false, code: "no_invite" });
    expect(await t.room.cancelInvite(alice, 1)).toEqual({ ok: true });
    expect((await t.room.meta())?.invites).toBeUndefined();
    expect(await t.room.acceptInvite(bob)).toMatchObject({ ok: false, code: "no_invite" });
  });

  it("can be sent again to another player after a refusal, and the new one replaces it", async () => {
    const t = await lobby();
    await t.room.invite(alice, 1, target(bob));
    await t.room.declineInvite(bob);
    expect(await t.room.invite(alice, 1, target(cy))).toEqual({ ok: true });
    expect((await t.room.meta())?.invites).toMatchObject([{ seat: 1, id: cy.id, status: "pending" }]);
  });

  it("does not let the game start while a seat waits for its answer; after the answer the host can start", async () => {
    const t = await lobby();
    await t.room.join(cy);
    await t.room.invite(alice, 2, target(bob));
    expect(await t.room.startGame(alice)).toMatchObject({ ok: false, code: "not_full" });
    await t.room.acceptInvite(bob);
    expect(await t.room.startGame(alice)).toEqual({ ok: true });
    expect((await t.room.meta())?.invites).toBeUndefined();
  });

  it("is refused once the game has started", async () => {
    const t = makeRoom();
    await t.room.init("g1", { players: 2 } as Options, none, false, alice);
    await t.room.join(bob);
    await t.room.startGame(alice);
    expect(await t.room.invite(alice, 1, target(cy))).toMatchObject({ ok: false, code: "not_in_lobby" });
    expect(await t.room.acceptInvite(cy)).toMatchObject({ ok: false, code: "not_in_lobby" });
  });
});
