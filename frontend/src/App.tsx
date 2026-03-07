import { useEffect, useMemo, useState } from "react";
import { Link, Route, Routes, useNavigate, useParams } from "react-router-dom";

import {
  api,
  ApiResult,
  Book,
  CritiqueResponse,
  formatError,
  GenerationStatus,
  KeyIdeasResponse,
  SearchBook,
} from "./api";
import { SearchBar } from "./components/search/SearchBar";
import { SearchResultsPanel } from "./components/search/SearchResultsPanel";

type SectionState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

const MAX_POLLS = 18;
const POLL_INTERVAL_MS = 5000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollSection<T extends { status: GenerationStatus; section: string }>(
  fetcher: () => Promise<ApiResult<T>>,
  section: string,
  endpoint: string,
  onUpdate: (state: SectionState<T>) => void,
  cancelled: () => boolean
): Promise<SectionState<T>> {
  let latestState: SectionState<T> = { data: null, loading: true, error: null };
  for (let attempt = 0; attempt <= MAX_POLLS; attempt += 1) {
    if (cancelled()) {
      return latestState;
    }

    try {
      const { data, meta } = await fetcher();
      const pending = data.status === "pending" || data.status === "generating";
      console.log("[poll]", {
        section,
        endpoint,
        attempt: attempt + 1,
        status: data.status,
        request_id: meta.requestId,
      });
      latestState = { data, loading: pending, error: null };
      onUpdate(latestState);

      if (!pending) {
        return latestState;
      }

      if (attempt === MAX_POLLS) {
        latestState = {
          data,
          loading: false,
          error: "Generation is taking longer than expected. Please refresh the page.",
        };
        onUpdate(latestState);
        return latestState;
      }

      await sleep(POLL_INTERVAL_MS);
    } catch (error) {
      latestState = { data: null, loading: false, error: formatError(error) };
      onUpdate(latestState);
      return latestState;
    }
  }

  return latestState;
}

function ErrorBox({ message }: { message: string }) {
  return <pre className="error-box">{message}</pre>;
}

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
      // Navigation should still proceed if prefetch fails.
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

function Skeleton() {
  return (
    <div className="skeleton">
      <div className="line" />
      <div className="line short" />
      <p>Please wait...</p>
    </div>
  );
}

function BookPage() {
  const { workId = "" } = useParams();
  const [book, setBook] = useState<Book | null>(null);
  const [bookError, setBookError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"key_ideas" | "critique">("key_ideas");

  const [keyIdeas, setKeyIdeas] = useState<SectionState<KeyIdeasResponse>>({
    data: null,
    loading: true,
    error: null,
  });
  const [critique, setCritique] = useState<SectionState<CritiqueResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let disposed = false;

    setBook(null);
    setBookError(null);
    setKeyIdeas({ data: null, loading: true, error: null });
    setCritique({ data: null, loading: true, error: null });

    void (async () => {
      try {
        const payload = await api.getBook(workId);
        if (!disposed) {
          setBook(payload);
        }
      } catch (error) {
        if (!disposed) {
          setBookError(formatError(error));
        }
      }
    })();

    void (async () => {
      const keyIdeasState = await pollSection(
        () => api.getKeyIdeasWithMeta(workId),
        "Key Ideas",
        `/api/books/${workId}/key-ideas`,
        (state) => {
          if (!disposed) {
            setKeyIdeas(state);
          }
        },
        () => disposed
      );

      if (disposed || keyIdeasState.data?.status !== "completed") {
        return;
      }

      await pollSection(
        () => api.getCritiqueWithMeta(workId),
        "Critique",
        `/api/books/${workId}/critique`,
        (state) => {
          if (!disposed) {
            setCritique(state);
          }
        },
        () => disposed
      );
    })();

    return () => {
      disposed = true;
    };
  }, [workId]);

  const meta = useMemo(() => {
    if (!book) {
      return null;
    }
    return (
      <section className="book-meta">
        {book.cover_url ? <img src={book.cover_url} alt={book.title} /> : <div className="placeholder">No Cover</div>}
        <div>
          <h1>{book.title}</h1>
          <p>{book.authors ?? "Unknown author"}</p>
          {book.description ? <p>{book.description}</p> : null}
        </div>
      </section>
    );
  }, [book]);

  const keyIdeasPane = () => {
    if (keyIdeas.loading) {
      return <Skeleton />;
    }
    if (keyIdeas.error) {
      return <ErrorBox message={keyIdeas.error} />;
    }
    if (keyIdeas.data?.status === "failed") {
      return (
        <ErrorBox
          message={`Section: ${keyIdeas.data.section}\nModel: ${keyIdeas.data.model ?? "unknown"}\nError: ${
            keyIdeas.data.error_message ?? "No details"
          }`}
        />
      );
    }
    return <pre className="content-box">{keyIdeas.data?.key_ideas ?? "No key ideas available."}</pre>;
  };

  const critiquePane = () => {
    if (critique.loading) {
      return <Skeleton />;
    }
    if (critique.error) {
      return <ErrorBox message={critique.error} />;
    }
    if (critique.data?.status === "failed") {
      return (
        <ErrorBox
          message={`Section: ${critique.data.section}\nModel: ${critique.data.model ?? "unknown"}\nError: ${
            critique.data.error_message ?? "No details"
          }`}
        />
      );
    }
    return (
      <div className="content-block">
        <h3>Strengths</h3>
        <p>{critique.data?.strengths ?? "Not available."}</p>
        <h3>Weaknesses</h3>
        <p>{critique.data?.weaknesses ?? "Not available."}</p>
        <h3>Who Should Read</h3>
        <p>{critique.data?.who_should_read ?? "Not available."}</p>
      </div>
    );
  };

  return (
    <main className="container">
      <p>
        <Link to="/">Back to Search</Link>
      </p>
      {bookError ? <ErrorBox message={bookError} /> : meta ?? <Skeleton />}

      <nav className="tabs">
        <button className={activeTab === "key_ideas" ? "active" : ""} onClick={() => setActiveTab("key_ideas")}>
          Key Ideas
        </button>
        <button className={activeTab === "critique" ? "active" : ""} onClick={() => setActiveTab("critique")}>
          Critique
        </button>
      </nav>

      <section className="tab-content">{activeTab === "key_ideas" ? keyIdeasPane() : critiquePane()}</section>
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<SearchPage />} />
      <Route path="/book/:workId" element={<BookPage />} />
    </Routes>
  );
}
