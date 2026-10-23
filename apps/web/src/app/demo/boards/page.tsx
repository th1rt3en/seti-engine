// The alien boards, with every place that a marker can go to, and with markers on every space: a page to look at (no sign-in, no server).
// `?pair=0..3` and `?variant=prompts|markers` show one board.
import { BoardsDemo } from "@/components/BoardsDemo";

export const metadata = { title: "Alien boards" };

export default async function Boards({ searchParams }: { searchParams: Promise<{ pair?: string; variant?: string }> }) {
  const q = await searchParams;
  const pair = q.pair !== undefined && /^[0-3]$/.test(q.pair) ? Number(q.pair) : null;
  const variant = q.variant === "prompts" || q.variant === "markers" ? q.variant : null;
  return <BoardsDemo pair={pair} variant={variant} />;
}
