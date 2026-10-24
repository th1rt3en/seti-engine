// The library: the things of the game to look at, one tab for each kind: the cards, the organizations and the quick start cards of the Space Agencies
// expansion, and the alien species boards. It shows what the engine's data and the pictures say; it works out no rule.
import { AlienLibrary, type AlienTile } from "@/components/AlienLibrary";
import { CardCatalog } from "@/components/CardCatalog";
import { cardImage } from "@/lib/cardImages";
import Link from "next/link";
import assets from "../../generated/assets.json";
import catalog from "../../generated/card-catalog.json";
import expansionAssets from "../../generated/expansion-assets.json";
import expansionImages from "../../generated/expansion-card-images.json";
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
const byNumber = (a: string, b: string): number => a.localeCompare(b, undefined, { numeric: true });
/** The cards of a species that are in the deck of the alien cards (the catalog is made from the engine's own data). */
const alienCards = (species: string) =>
  (catalog as { id: string; name: string; deck: string; species: string | null }[])
    .filter((c) => c.deck === "alien" && c.species === species)
    .sort((a, b) => byNumber(a.id, b.id));
/** The exploration cards of Arkhos ("ET 33" to "ET 41"): their pictures are among the cards of the expansion, but they are not in the main deck of the catalog. */
const EXPLORATION = Object.keys(expansionImages as Record<string, string>)
  .filter((id) => /^ET \d+$/.test(id))
  .sort(byNumber);

/** A species with one kind of card has one section; Arkhos has two: the exploration cards and the security cards. */
function tile(key: string, name: string, src: string | undefined, expansion = false): AlienTile {
  const cards = alienCards(key);
  if (key === "arkhos") {
    return {
      key,
      name,
      src,
      expansion,
      sections: [
        {
          label: "Exploration cards",
          note: "The deck that the markers of the Arkhos board explore: a minor reward for each marker, a major one when a card is explored.",
          cards: EXPLORATION.map((id) => ({ id })),
        },
        {
          label: "Security cards",
          note: "Each player is dealt one for every trace color; it is breached from an overflow space.",
          cards: cards.map((c) => ({ id: c.id, caption: `${c.id} ${c.name}` })),
        },
      ],
    };
  }
  return { key, name, src, expansion, sections: [{ label: "Alien cards", cards: cards.map((c) => ({ id: c.id })) }] };
}

const ALIENS: AlienTile[] = [
  tile("anomalies", "Anomalies", SPECIES.anomalies),
  tile("centaurians", "Centaurians", SPECIES.centaurians),
  tile("exertians", "Exertians", SPECIES.exertians),
  tile("mascamites", "Mascamites", SPECIES.mascamites),
  tile("oumuamua", "'Oumuamua", SPECIES.oumuamua),
  tile("arkhos", "Arkhos", EXPANSION["boards/arkhos"], true),
  tile("glyphids", "Glyphids", EXPANSION["boards/glyphids"], true),
  tile("amoeba", "Amoeba", EXPANSION["boards/amoeba"], true),
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
            {QUICK.map(([id]) => (
              <figure key={id}>
                <img src={cardImage(id)} alt={`Quick start card ${id}`} loading="lazy" />
                <figcaption className="muted small">{id}</figcaption>
              </figure>
            ))}
          </div>
        </>
      ) : null}
      {current === "aliens" ? (
        <>
          <p className="muted">The alien species boards. Two species, chosen at random, are in a game; the expansion adds three more.</p>
          <AlienLibrary aliens={ALIENS} />
        </>
      ) : null}
    </>
  );
}
