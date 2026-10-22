// The links to the previous and the next page of a list (nothing when there is one page). `link` makes the address of a page.
import Link from "next/link";

export function Pager({ page, pages, link }: { page: number; pages: number; link: (page: number) => string }) {
  if (pages <= 1) return null;
  return (
    <nav className="pager" aria-label="Pages">
      {page > 1 ? (
        <Link href={link(page - 1)} className="btn small ghost">
          ← Newer
        </Link>
      ) : (
        <span />
      )}
      <span className="muted small">
        Page {page} of {pages}
      </span>
      {page < pages ? (
        <Link href={link(page + 1)} className="btn small ghost">
          Older →
        </Link>
      ) : (
        <span />
      )}
    </nav>
  );
}
