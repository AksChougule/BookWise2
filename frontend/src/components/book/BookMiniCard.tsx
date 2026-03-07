import { AuthorBookItem } from "../../api";

type BookMiniCardProps = {
  book: AuthorBookItem;
};

export function BookMiniCard({ book }: BookMiniCardProps) {
  return (
    <article className="book-mini-card">
      {book.cover_url ? (
        <img src={book.cover_url} alt={book.title} className="book-mini-cover" />
      ) : (
        <div className="book-mini-cover book-mini-cover-placeholder">No cover</div>
      )}
      <div>
        <p className="book-mini-title">{book.title}</p>
        <p className="book-mini-meta">{book.authors ?? "Unknown author"}</p>
        <p className="book-mini-meta">{book.first_publish_year ?? "Unknown year"}</p>
      </div>
    </article>
  );
}
