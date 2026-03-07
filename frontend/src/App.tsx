import { useEffect, useState } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";

import { api, formatError, SearchBook } from "./api";
import { BookDetailsPage } from "./components/book/BookDetailsPage";
import { SearchBar } from "./components/search/SearchBar";
import { SearchResultsPanel } from "./components/search/SearchResultsPanel";

function SearchPage() {
  const navigate = useNavigate();
  const [queryInput, setQueryInput] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchBook[]>([]);
  const [prefetchingId, setPrefetchingId] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setQuery(queryInput.trim());
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [queryInput]);

  useEffect(() => {
    let disposed = false;
    if (!query) {
      setResults([]);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    void (async () => {
      try {
        const response = await api.search(query);
        if (!disposed) {
          setResults(response.results.slice(0, 25));
        }
      } catch (err) {
        if (!disposed) {
          setResults([]);
          setError(formatError(err));
        }
      } finally {
        if (!disposed) {
          setLoading(false);
        }
      }
    })();

    return () => {
      disposed = true;
    };
  }, [query]);

  const onOpenResult = async (book: SearchBook) => {
    setPrefetchingId(book.work_id);
    try {
      await api.getBook(book.work_id);
    } catch {
      // continue to navigation even when prefetch fails
    } finally {
      setPrefetchingId(null);
      navigate(`/book/${book.work_id}`);
    }
  };

  const onSurprise = async () => {
    setError(null);
    try {
      const pick = await api.surprise();
      navigate(`/book/${pick.work_id}`);
    } catch (err) {
      setError(formatError(err));
    }
  };

  return (
    <main className="container">
      <header className="hero">
        <h1>BookWise 2</h1>
        <p>Search Open Library, then auto-generate Key Ideas and Critique.</p>
      </header>

      <SearchBar value={queryInput} loading={loading} onChange={setQueryInput} onSurprise={onSurprise} />
      <SearchResultsPanel
        query={queryInput}
        loading={loading}
        error={error}
        results={results}
        prefetchingId={prefetchingId}
        onOpen={onOpenResult}
      />
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<SearchPage />} />
      <Route path="/book/:workId" element={<BookDetailsPage />} />
    </Routes>
  );
}
