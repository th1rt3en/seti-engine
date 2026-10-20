import type { ReactNode } from "react";

// Buttons laid over a card that the player has picked (a card of the hand, a card of the display): what can be done with it, each as a button on the
// card itself. A button can be greyed out with the reason as its tooltip, or carry a warning (the move is allowed but gives nothing).
export interface CardAction {
  key: string;
  label: ReactNode;
  onClick: () => void;
  primary?: boolean;
  disabled?: boolean;
  /** Why the button is greyed out, or what the move does. */
  title?: string;
  /** The move is allowed but the player should know it does little or nothing. */
  warn?: string;
}

export function CardActions({ actions }: { actions: CardAction[] }) {
  if (actions.length === 0) return null;
  return (
    <span className="cardactions">
      {actions.map((a) => (
        <span key={a.key} className="cardaction">
          <button
            type="button"
            className={a.warn ? "primary warn" : a.primary ? "primary" : "secondary"}
            disabled={a.disabled}
            title={a.title}
            onClick={a.onClick}
          >
            {a.label}
          </button>
          {a.warn ? <span className="cardwarn">{a.warn}</span> : null}
        </span>
      ))}
    </span>
  );
}
