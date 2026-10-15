// Places on the picture of a panel beside the board that a move can be made at (the holes of the Glyphids translation board, the organelle
// spaces of the Amoeba board, ...). They are drawn like the places on the board itself, so the player clicks the highlighted place.
import type { Spot } from "@/lib/targets";
import type { BoardSpots } from "./BoardView";

/** The spots of one panel, as SVG groups for the panel's own picture. `render` can draw something in a place (a glyph token) before it is clickable. */
export function PanelSpots({
  spots,
  panel,
  render,
}: {
  spots?: BoardSpots;
  panel: NonNullable<Spot["panel"]>;
  render?: (spot: Spot, index: number) => React.ReactNode;
}) {
  const items = spots?.items.filter((sp) => sp.panel === panel) ?? [];
  if (!spots || items.length === 0) return null;
  return (
    <>
      {items.map((sp, k) => (
        <g
          key={sp.id}
          // biome-ignore lint/a11y/useSemanticElements: an SVG group cannot be a button element
          role="button"
          tabIndex={0}
          aria-label={sp.label}
          className={spots.selected === sp.id ? "spot chosen" : "spot"}
          onClick={() => spots.onSelect(sp.id)}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && spots.onSelect(sp.id)}
        >
          {sp.shape.kind === "circle" ? <circle cx={sp.shape.x} cy={sp.shape.y} r={sp.shape.r} className="spotshape panelspot" /> : null}
          {render?.(sp, k)}
        </g>
      ))}
    </>
  );
}
