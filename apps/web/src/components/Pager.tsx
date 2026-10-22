// The links to the previous and the next page of a list (nothing when there is one page). `link` makes the address of a page (a server component: the
// function stays here, the links are client components that show a spinner while their page loads, see PagerLink).
import { PagerLink } from "./PagerLink";

export function Pager({
  page,
  pages,
  link,
  labels = ["← Newer", "Older →"],
}: { page: number; pages: number; link: (page: number) => string; labels?: [string, string] }) {
  if (pages <= 1) return null;
  return (
    <nav className="pager" aria-label="Pages">
      {page > 1 ? <PagerLink href={link(page - 1)} label={labels[0]} /> : <span />}
      <span className="muted small">
        Page {page} of {pages}
      </span>
      {page < pages ? <PagerLink href={link(page + 1)} label={labels[1]} /> : <span />}
    </nav>
  );
}
