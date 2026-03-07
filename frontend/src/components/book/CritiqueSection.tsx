import { CritiqueResponse } from "../../api";
import { Button } from "../ui/button";

type CritiqueSectionProps = {
  state: {
    data: CritiqueResponse | null;
    loading: boolean;
    error: string | null;
  };
  onRetry: () => void;
};

export function CritiqueSection({ state, onRetry }: CritiqueSectionProps) {
  if (state.loading) {
    return (
      <div className="skeleton">
        <div className="line" />
        <div className="line short" />
        <p>Loading critique…</p>
      </div>
    );
  }

  if (state.error || state.data?.status === "failed") {
    return (
      <div>
        <pre className="error-box">{state.error ?? state.data?.error_message ?? "Critique generation failed."}</pre>
        <Button className="retry-button" onClick={onRetry}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="content-block">
      <h3>Strengths</h3>
      <p>{state.data?.strengths ?? "Not available."}</p>
      <h3>Weaknesses</h3>
      <p>{state.data?.weaknesses ?? "Not available."}</p>
      <h3>Who Should Read</h3>
      <p>{state.data?.who_should_read ?? "Not available."}</p>
    </div>
  );
}
