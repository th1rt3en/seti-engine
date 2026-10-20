// The library: the things of the game to look at, one tab for each kind: the cards, the organizations and the quick start cards of the Space Agencies
// expansion, and the alien species boards. It shows what the engine's data and the pictures say; it works out no rule.
import { CardCatalog } from "@/components/CardCatalog";
import { cardImage } from "@/lib/cardImages";
import Link from "next/link";
import assets from "../../generated/assets.json";
import expansionAssets from "../../generated/expansion-assets.json";
import organizations from "../../generated/organizations.json";
import quickStart from "../../generated/quick-start.json";

export const metadata = { title: "Library" };

const TABS = [
  { key: "cards", label: "Cards" },
  { key: "organizations", label: "Organizations" },
  { key: "quickstart", label: "Quick start cards" },
  { key: "aliens", label: "Alien boards" },
] as const;
type TabKey = (typeof TABS)[number]["key"];

const ORGS = Object.entries(
  organizations as unknown as Record<
    string,
    { name: string; number: number; abilities: Record<string, string>; income: Record<string, number> }
  >,
).sort((a, b) => a[1].number - b[1].number);
const QUICK = Object.entries(quickStart as unknown as Record<string, { marks: string }>).sort((a, b) =>
  a[0].localeCompare(b[0], undefined, { numeric: true }),
);
const EXPANSION = expansionAssets as Record<string, string>;
const SPECIES = assets.species as Record<string, string>;
const ALIENS: { name: string; src: string | undefined; expansion?: boolean }[] = [
  { name: "Anomalies", src: SPECIES.anomalies },
  { name: "Centaurians", src: SPECIES.centaurians },
  { name: "Exertians", src: SPECIES.exertians },
  { name: "Mascamites", src: SPECIES.mascamites },
  { name: "'Oumuamua", src: SPECIES.oumuamua },
  { name: "Arkhos", src: EXPANSION["boards/arkhos"], expansion: true },
  { name: "Glyphids", src: EXPANSION["boards/glyphids"], expansion: true },
  { name: "Amoeba", src: EXPANSION["boards/amoeba"], expansion: true },
];

export default async function LibraryPage({ searchParams }: { searchParams: Promise<{ tab?: string }> }) {
  const { tab } = await searchParams;
  const current: TabKey = TABS.find((t) => t.key === tab)?.key ?? "cards";
  return (
    <>
      <h1>Library</h1>
      <nav className="libtabs" aria-label="Library">
        {TABS.map((t) => (
          <Link
            key={t.key}
            href={t.key === "cards" ? "/library" : `/library?tab=${t.key}`}
            aria-current={t.key === current ? "page" : undefined}
          >
            {t.label}
          </Link>
        ))}
      </nav>
      {current === "cards" ? (
        <>
          <p className="muted">
            Every card of the main deck, the alien decks and the Space Agencies deck. Hover a card for a second to see it large.
          </p>
          <CardCatalog />
        </>
      ) : null}
      {current === "organizations" ? (
        <>
          <p className="muted">
            The organizations of the Space Agencies expansion. Each player takes one at the start of a game that plays with them.
          </p>
          <div className="libgrid wide">
            {ORGS.map(([id, o]) => (
              <figure key={id}>
                <img src={cardImage(id)} alt={o.name} loading="lazy" />
                <figcaption>
                  <b>{o.name}</b>
                  {o.abilities.passive ? <span className="muted small">{o.abilities.passive}</span> : null}
                  {o.abilities.mainAction ? <span className="muted small">Main action: {o.abilities.mainAction}</span> : null}
                  {o.abilities.freeAction ? <span className="muted small">Free action: {o.abilities.freeAction}</span> : null}
                </figcaption>
              </figure>
            ))}
          </div>
        </>
      ) : null}
      {current === "quickstart" ? (
        <>
          <p className="muted">The quick start cards of the expansion. A player is dealt three of them and keeps two.</p>
          <div className="libgrid">
            {QUICK.map(([id, q]) => (
              <figure key={id}>
                <img src={cardImage(id)} alt={`Quick start card ${id}`} loading="lazy" />
                <figcaption className="muted small">Marks {q.marks}</figcaption>
              </figure>
            ))}
          </div>
        </>
      ) : null}
      {current === "aliens" ? (
        <>
          <p className="muted">The alien species boards. Two species, chosen at random, are in a game; the expansion adds three more.</p>
          <div className="libgrid aliens">
            {ALIENS.map((a) => (
              <figure key={a.name}>
                <img src={a.src} alt={`${a.name} board`} loading="lazy" />
                <figcaption>
                  <b>{a.name}</b>
                  {a.expansion ? <span className="muted small">Space Agencies</span> : null}
                </figcaption>
              </figure>
            ))}
          </div>
        </>
      ) : null}
    </>
  );
}
