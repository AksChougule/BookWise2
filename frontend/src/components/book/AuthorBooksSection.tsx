import { AuthorBooksResponse } from "../../api";
import { AuthorGroup } from "./AuthorGroup";

type SectionState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

type AuthorBooksSectionProps = {
  state: SectionState<AuthorBooksResponse>;
};

export function AuthorBooksSection({ state }: AuthorBooksSectionProps) {
  if (state.loading) {
    return (
      <div className="placeholder">
        <p>Loading other books by the same author…</p>
        <p className="muted-small">Please wait while we fetch related titles.</p>
      </div>
    );
  }

  if (state.error) {
    return <pre className="error-box">{state.error}</pre>;
  }

  if (!state.data || state.data.groups.length === 0) {
    return <p className="placeholder-copy">No author groups available yet.</p>;
  }

  return (
    <div className="author-groups-wrap section-body">
      {state.data.groups.map((group) => (
        <AuthorGroup key={group.author} group={group} />
      ))}
    </div>
  );
}
