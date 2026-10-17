import { CardCatalog } from "@/components/CardCatalog";

export const metadata = { title: "Cards" };

export default function CardsPage() {
  return (
    <>
      <h1>Cards</h1>
      <p className="muted">
        Every card of the main deck, the alien decks and the Space Agencies deck. Hover a card for a second to see it large.
      </p>
      <CardCatalog />
    </>
  );
}
