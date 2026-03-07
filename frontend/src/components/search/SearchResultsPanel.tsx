import { SearchBook } from "../../api";
import { SearchResultCard } from "./SearchResultCard";
import { ScrollArea } from "../ui/scroll-area";

type SearchResultsPanelProps = {
  query: string;
  loading: boolean;
  error: string | null;
  results: SearchBook[];
  prefetchingId: string | null;
  onOpen: (book: SearchBook) => void;
};

export function SearchResultsPanel({
  query,
  loading,
  error,
  results,
  prefetchingId,
  onOpen,
}: SearchResultsPanelProps) {
  if (!query.trim()) {
    return null;
  }

  if (loading) {
    return <p className="search-hint">Searching...</p>;
  }

  if (error) {
    return <pre className="error-box">{error}</pre>;
  }

  if (results.length === 0) {
    return <p className="search-hint">No books found.</p>;
  }

  return (
    <ScrollArea className="search-results-panel">
      <div className="search-results-grid">
        {results.slice(0, 25).map((book) => (
          <SearchResultCard
            key={book.work_id}
            book={book}
            prefetching={prefetchingId === book.work_id}
            onOpen={onOpen}
          />
        ))}
      </div>
    </ScrollArea>
  );
}
