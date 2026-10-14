// A card image (generated/assets.json). A hidden card ("?") is shown as a card back. The files are small WebP images with the hash of their
// content in the name, so Cloudflare and the browser keep them for good.
import { cardName } from "@/lib/moves";
import assets from "../generated/assets.json";

const CARDS = assets.cards as Record<string, string>;

export function CardImage({ id, width = 120, title }: { id: string; width?: number; title?: string }) {
  const height = Math.round((width * 1040) / 747);
  const src = CARDS[id];
  if (id === "?" || src === undefined) {
    return (
      <span className="cardback" style={{ width, height }} title={title ?? (id === "?" ? "hidden card" : id)}>
        {id === "?" ? "?" : id}
      </span>
    );
  }
  return (
    <img
      className="cardimg"
      src={src}
      alt={cardName(id)}
      title={title ?? cardName(id)}
      width={width}
      height={height}
      loading="lazy"
      decoding="async"
    />
  );
}
