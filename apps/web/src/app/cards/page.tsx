import { redirect } from "next/navigation";

// the cards are the first tab of the library
export default function CardsPage(): never {
  redirect("/library");
}
