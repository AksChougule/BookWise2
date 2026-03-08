import { ExploreLinksResponse } from "../../api";

type SectionState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

type ExploreMoreSectionProps = {
  state: SectionState<ExploreLinksResponse>;
};

export function ExploreMoreSection({ state }: ExploreMoreSectionProps) {
  if (state.loading) {
    return (
      <div className="placeholder">
        <p>Resolving external links…</p>
        <p className="muted-small">Please wait while we prepare Explore More resources.</p>
      </div>
    );
  }

  if (state.error) {
    return <pre className="error-box">{state.error}</pre>;
  }

  if (!state.data) {
    return <p className="placeholder-copy">No external links available yet.</p>;
  }

  return (
    <div className="explore-links-grid section-body">
      <a href={state.data.amazon_url} target="_blank" rel="noreferrer noopener" className="explore-link-card">
        <p className="explore-link-title">Amazon</p>
        <p className="explore-link-meta">Open external link</p>
      </a>

      <a href={state.data.goodreads_url} target="_blank" rel="noreferrer noopener" className="explore-link-card">
        <p className="explore-link-title">Goodreads</p>
        <p className="explore-link-meta">Open external link</p>
      </a>

      {state.data.author_website ? (
        <a
          href={state.data.author_website}
          target="_blank"
          rel="noreferrer noopener"
          className="explore-link-card"
        >
          <p className="explore-link-title">Author Website</p>
          <p className="explore-link-meta">Open external link</p>
        </a>
      ) : (
        <div className="explore-link-card muted-card">
          <p className="explore-link-title">Author Website</p>
          <p className="explore-link-meta">Not confidently identified for this book.</p>
        </div>
      )}
    </div>
  );
}
