// Small symbols for the resources: credit, energy and cards (a card of the display and a card of the deck have different symbols).
// Drawn here until the owner supplies the printed symbols (docs/asset-gaps.md).
import assets from "../generated/assets.json";

const SIZE = 22;

/** The globe of the scoring track: the icon of victory points, wherever a score is shown. */
export function ScoreIcon({ size = SIZE }: { size?: number }) {
  return (
    <img
      src={assets.scoreIcon}
      alt="points"
      title="Victory points"
      width={size}
      height={size}
      className="resicon scoreicon"
      decoding="async"
    />
  );
}

/** The hexagon icon of a main action, as printed on the player aid. */
export function ActionIcon({ name, size = 30 }: { name: string; size?: number }) {
  const src = (assets.actionIcons as Record<string, string>)[name];
  if (!src) return null;
  return <img src={src} alt="" width={size} height={Math.round(size * 1.1)} className="resicon actionicon" decoding="async" />;
}

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

/** Publicity: the red pennant with a microphone, as printed. */
export function PublicityIcon({ size = SIZE }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label="publicity" className="resicon">
      <title>Publicity</title>
      <path d="M2 3h15l5 9-5 9H2z" fill="#e0452f" stroke="#8a2112" strokeWidth="1.4" strokeLinejoin="round" />
      <rect x="9" y="6" width="5" height="9" rx="2.5" fill="#fff" />
      <path d="M7.5 12a4.5 4.5 0 0 0 9 0M12 16.5V19" fill="none" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

/** A data token: the blue glossy disc. */
export function DataIcon({ size = SIZE }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label="data" className="resicon">
      <title>Data</title>
      <circle cx="12" cy="12" r="10.5" fill="#2f7be0" stroke="#173f7a" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="7.5" fill="none" stroke="#fff" strokeOpacity="0.55" strokeWidth="1.2" />
      <path d="M7 9.5h10M7 12.5h6M7 15.5h8" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

/** A card of an alien species: the alien head on a teal hexagon. */
export function AlienCardIcon({ size = SIZE }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label="alien card" className="resicon">
      <title>Alien card</title>
      <path d="M12 1.5 21.5 7v10L12 22.5 2.5 17V7z" fill="#1f8f7a" stroke="#0d4a3f" strokeWidth="1.4" />
      <path d="M12 6c3.4 0 5.4 2.4 5.4 5 0 2.6-2.3 5.6-5.4 6.6C8.9 16.600 6.600 13.600 6.600 11c0-2.600 2-5 5.400-5z" fill="#fff" />
      <ellipse cx="9.600" cy="11" rx="1.400" ry="2.200" transform="rotate(-25 9.600 11)" fill="#0d4a3f" />
      <ellipse cx="14.400" cy="11" rx="1.400" ry="2.200" transform="rotate(25 14.400 11)" fill="#0d4a3f" />
    </svg>
  );
}

/** An exofossil of 'Oumuamua. */
export function ExofossilIcon({ size = SIZE }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label="exofossil" className="resicon">
      <title>Exofossil</title>
      <ellipse cx="12" cy="12" rx="10" ry="7" fill="#b89a6a" stroke="#6b5530" strokeWidth="1.4" transform="rotate(-20 12 12)" />
      <path d="M5 13c3-6 9-8 14-4" fill="none" stroke="#6b5530" strokeWidth="1.2" />
    </svg>
  );
}

/** A signal token of the Space Agencies expansion. */
export function SignalTokenIcon({ size = SIZE }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label="signal token" className="resicon">
      <title>Signal token</title>
      <circle cx="12" cy="12" r="10" fill="#7c4dff" stroke="#3b1f99" strokeWidth="1.4" />
      <path d="M7 12a5 5 0 0 1 10 0M9.500 12a2.500 2.500 0 0 1 5 0" fill="none" stroke="#fff" strokeWidth="1.500" strokeLinecap="round" />
      <circle cx="12" cy="12.500" r="1.200" fill="#fff" />
    </svg>
  );
}

/** A trace of life: three dots in the colours of the three kinds. */
export function TraceIcon({ size = SIZE }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label="trace" className="resicon">
      <title>Trace</title>
      <circle cx="7" cy="16" r="5" fill="#e0457b" />
      <circle cx="17" cy="16" r="5" fill="#2f8fd8" />
      <circle cx="12" cy="7.500" r="5" fill="#e0a800" />
    </svg>
  );
}
