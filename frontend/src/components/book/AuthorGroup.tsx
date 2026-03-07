import { AuthorBooksGroup } from "../../api";
import { BookMiniCard } from "./BookMiniCard";

type AuthorGroupProps = {
  group: AuthorBooksGroup;
};

export function AuthorGroup({ group }: AuthorGroupProps) {
  return (
    <section className="author-group">
      <h3>{group.author}</h3>
      {group.books.length ? (
        <div className="author-books-grid">
          {group.books.map((book) => (
            <BookMiniCard key={`${group.author}-${book.work_id}`} book={book} />
          ))}
        </div>
      ) : (
        <p className="placeholder-copy">No related books found for this author yet.</p>
      )}
    </section>
  );
}
