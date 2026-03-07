import { Link } from "react-router-dom";

import { Book } from "../../api";
import { SectionNav } from "./SectionNav";

type StickyBookRailProps = {
  book: Book | null;
  activeId: string;
  sectionItems: Array<{ id: string; label: string }>;
  onNavigate: (id: string) => void;
};

export function StickyBookRail({ book, activeId, sectionItems, onNavigate }: StickyBookRailProps) {
  return (
    <aside className="sticky-rail desktop-only">
      <p>
        <Link to="/">Return to search results</Link>
      </p>
      <div className="rail-cover-wrap">
        {book?.cover_url ? (
          <img src={book.cover_url} alt={book.title} className="rail-cover" />
        ) : (
          <div className="placeholder rail-cover">No Cover</div>
        )}
      </div>
      <SectionNav items={sectionItems} activeId={activeId} onNavigate={onNavigate} />
    </aside>
  );
}
