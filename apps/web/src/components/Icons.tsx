// Small symbols for the resources: credit, energy and cards (a card of the display and a card of the deck have different symbols).
// Drawn here until the owner supplies the printed symbols (docs/asset-gaps.md).
const SIZE = 22;

export function CreditIcon({ size = SIZE }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label="credit" className="resicon">
      <title>Credit</title>
      <circle cx="12" cy="12" r="10.5" fill="#e0b000" stroke="#7a5a00" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="7.2" fill="none" stroke="#fff3b0" strokeWidth="1.3" />
      <path d="M14.6 8.6A3.6 3.6 0 1 0 14.6 15.4" fill="none" stroke="#5c4300" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function EnergyIcon({ size = SIZE }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label="energy" className="resicon">
      <title>Energy</title>
      <rect x="1.5" y="1.5" width="21" height="21" rx="5" fill="#3fae49" stroke="#1f6b27" strokeWidth="1.5" />
      <path d="M13.5 3.5 6.5 13.2h4.4L9.8 20.5l7.7-10.2h-4.6z" fill="#fff" />
    </svg>
  );
}

/** A card of the card row (the display): a card with the row's three cards beside it. */
export function DisplayCardIcon({ size = SIZE }: { size?: number }) {
  return (
    <svg width={size * 1.4} height={size} viewBox="0 0 34 24" role="img" aria-label="card of the display" className="resicon">
      <title>Card of the display</title>
      <rect x="1" y="3" width="9" height="14" rx="1.5" fill="#2a3b55" stroke="#9fb6d8" strokeWidth="1" />
      <rect x="12" y="3" width="9" height="14" rx="1.5" fill="#2a3b55" stroke="#9fb6d8" strokeWidth="1" />
      <rect x="23" y="1" width="10" height="16" rx="1.5" fill="#f2f6fb" stroke="#fff" strokeWidth="1.5" />
      <path d="M28 5v8M24.5 9h7" stroke="#2a6ad6" strokeWidth="2" strokeLinecap="round" />
      <path d="M2 21h31" stroke="#9fb6d8" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

/** A card from the top of the deck: a stack of face-down cards. */
export function DeckCardIcon({ size = SIZE }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label="card of the deck" className="resicon">
      <title>Card from the top of the deck</title>
      <rect x="6" y="2" width="14" height="18" rx="2" fill="#1d2840" stroke="#7d93b8" strokeWidth="1" />
      <rect x="4" y="4" width="14" height="18" rx="2" fill="#243350" stroke="#9fb6d8" strokeWidth="1" />
      <rect x="2" y="6" width="14" height="16" rx="2" fill="#2f4570" stroke="#cfdcf0" strokeWidth="1.2" />
      <circle cx="9" cy="14" r="3.2" fill="none" stroke="#cfdcf0" strokeWidth="1.3" />
      <path d="M9 10.8v6.4M5.8 14h6.4" stroke="#cfdcf0" strokeWidth="1" />
    </svg>
  );
}
