import { SearchBook } from "../../api";
import { Button } from "../ui/button";
import { Card } from "../ui/card";

type SearchResultCardProps = {
  book: SearchBook;
  prefetching: boolean;
  onOpen: (book: SearchBook) => void;
};

export function SearchResultCard({ book, prefetching, onOpen }: SearchResultCardProps) {
  return (
    <Card className="search-result-card">
      {book.cover_url ? (
        <img src={book.cover_url} alt={book.title} className="search-result-cover" />
      ) : (
        <div className="search-result-cover search-result-placeholder">No Cover</div>
      )}
      <div className="search-result-body">
        <h3>{book.title}</h3>
        <p>{book.authors ?? "Unknown author"}</p>
        <p className="search-result-year">
          First published: {book.first_publish_year ? String(book.first_publish_year) : "Unknown"}
        </p>
        <Button className="search-result-button" onClick={() => onOpen(book)} disabled={prefetching}>
          {prefetching ? "Prefetching..." : "Open Book"}
        </Button>
      </div>
    </Card>
  );
}
