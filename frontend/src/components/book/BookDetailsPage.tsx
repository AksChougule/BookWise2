import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  api,
  ApiResult,
  Book,
  CritiqueResponse,
  formatError,
  GenerationStatus,
  KeyIdeasResponse,
  SummaryResponse,
} from "../../api";
import { CritiqueSection } from "./CritiqueSection";
import { KeyIdeasSection } from "./KeyIdeasSection";
import { SectionContainer } from "./SectionContainer";
import { StickyBookRail } from "./StickyBookRail";
import { SummarySection } from "./SummarySection";

type SectionState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

const MAX_POLLS = 18;
const POLL_INTERVAL_MS = 5000;

const SECTION_ITEMS = [
  { id: "summary", label: "Summary" },
  { id: "key-ideas", label: "Key Ideas" },
  { id: "critique", label: "Critique" },
  { id: "other-books", label: "Other Books by Same Author" },
  { id: "youtube-videos", label: "YouTube Videos" },
  { id: "explore-more", label: "Explore More" },
] as const;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollSection<T extends { status: GenerationStatus }>(
  fetcher: () => Promise<ApiResult<T>>,
  onUpdate: (state: SectionState<T>) => void,
  cancelled: () => boolean
): Promise<SectionState<T>> {
  let latestState: SectionState<T> = { data: null, loading: true, error: null };
  for (let attempt = 0; attempt <= MAX_POLLS; attempt += 1) {
    if (cancelled()) {
      return latestState;
    }

    try {
      const { data } = await fetcher();
      const pending = data.status === "pending" || data.status === "generating";
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

export function BookDetailsPage() {
  const { workId = "" } = useParams();
  const [book, setBook] = useState<Book | null>(null);
  const [bookError, setBookError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string>("summary");

  const [summary, setSummary] = useState<SectionState<SummaryResponse>>({
    data: null,
    loading: true,
    error: null,
  });
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

  const runSections = async (retry: { summary?: boolean; keyIdeas?: boolean; critique?: boolean } = {}) => {
    let disposed = false;
    const cancelled = () => disposed;

    const summaryState = await pollSection(
      () => api.getSummaryWithMeta(workId, Boolean(retry.summary)),
      setSummary,
      cancelled
    );

    if (cancelled() || summaryState.data?.status !== "completed") {
      return () => {
        disposed = true;
      };
    }

    const keyIdeasState = await pollSection(
      () => api.getKeyIdeasWithMeta(workId, Boolean(retry.keyIdeas)),
      setKeyIdeas,
      cancelled
    );

    if (cancelled() || keyIdeasState.data?.status !== "completed") {
      return () => {
        disposed = true;
      };
    }

    await pollSection(
      () => api.getCritiqueWithMeta(workId, Boolean(retry.critique)),
      setCritique,
      cancelled
    );

    return () => {
      disposed = true;
    };
  };

  useEffect(() => {
    let disposed = false;

    setBook(null);
    setBookError(null);
    setSummary({ data: null, loading: true, error: null });
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

    void runSections();

    return () => {
      disposed = true;
    };
  }, [workId]);

  useEffect(() => {
    const sections = Array.from(document.querySelectorAll<HTMLElement>("[data-section-id]"));
    if (!sections.length) {
      return;
    }

    const activationOffset = 120;

    const computeActiveSection = () => {
      let nextActive = sections[0]?.dataset.sectionId ?? "summary";

      for (const section of sections) {
        const sectionId = section.dataset.sectionId;
        if (!sectionId) {
          continue;
        }

        const rect = section.getBoundingClientRect();
        if (rect.top <= activationOffset) {
          nextActive = sectionId;
        } else {
          break;
        }
      }

      setActiveSection((current) => (current === nextActive ? current : nextActive));
    };

    computeActiveSection();
    window.addEventListener("scroll", computeActiveSection, { passive: true });
    window.addEventListener("resize", computeActiveSection);

    return () => {
      window.removeEventListener("scroll", computeActiveSection);
      window.removeEventListener("resize", computeActiveSection);
    };
  }, [summary.data, keyIdeas.data, critique.data]);

  const onNavigate = (id: string) => {
    setActiveSection(id);
    const target = document.getElementById(id);
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const onMobileNavigate = (id: string) => {
    setActiveSection(id);
    onNavigate(id);
  };

  const mobileHeader = useMemo(() => {
    return (
      <header className="mobile-book-header mobile-only">
        <div className="mobile-book-meta">
          {book?.cover_url ? (
            <img src={book.cover_url} alt={book.title} className="mobile-cover" />
          ) : (
            <div className="placeholder mobile-cover">No Cover</div>
          )}
          <div>
            <p className="mobile-title">{book?.title ?? "Loading book..."}</p>
            <p className="mobile-author">{book?.authors ?? "Unknown author"}</p>
          </div>
        </div>
        <label className="mobile-nav-label">
          Jump to section
          <select value={activeSection} onChange={(e) => onMobileNavigate(e.target.value)}>
            {SECTION_ITEMS.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </header>
    );
  }, [activeSection, book]);

  return (
    <main className="container">
      {mobileHeader}
      <div className="book-details-layout">
        <StickyBookRail book={book} activeId={activeSection} sectionItems={[...SECTION_ITEMS]} onNavigate={onNavigate} />

        <div className="details-content">
          <p className="mobile-only">
            <Link to="/">Return to search results</Link>
          </p>

          {bookError ? <pre className="error-box">{bookError}</pre> : null}

          <SectionContainer id="summary" title="Summary">
            <SummarySection state={summary} onRetry={() => void runSections({ summary: true })} />
          </SectionContainer>

          <SectionContainer id="key-ideas" title="Key Ideas">
            <KeyIdeasSection state={keyIdeas} onRetry={() => void runSections({ keyIdeas: true })} />
          </SectionContainer>

          <SectionContainer id="critique" title="Critique">
            <CritiqueSection state={critique} onRetry={() => void runSections({ critique: true })} />
          </SectionContainer>

          <SectionContainer id="other-books" title="Other Books by Same Author">
            <p className="placeholder-copy">Section scaffolded for Sprint 3.</p>
          </SectionContainer>

          <SectionContainer id="youtube-videos" title="YouTube Videos">
            <p className="placeholder-copy">Section scaffolded for Sprint 3.</p>
          </SectionContainer>

          <SectionContainer id="explore-more" title="Explore More">
            <p className="placeholder-copy">Section scaffolded for Sprint 3.</p>
          </SectionContainer>
        </div>
      </div>
    </main>
  );
}
