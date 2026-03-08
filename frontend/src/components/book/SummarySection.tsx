import { SummaryResponse } from "../../api";
import { Button } from "../ui/button";

type SummarySectionProps = {
  state: {
    data: SummaryResponse | null;
    loading: boolean;
    error: string | null;
  };
  onRetry: () => void;
};

export function SummarySection({ state, onRetry }: SummarySectionProps) {
  if (state.loading) {
    return (
      <div className="skeleton">
        <div className="line" />
        <div className="line short" />
        <p>Loading summary…</p>
      </div>
    );
  }

  if (state.error) {
    return (
      <div>
        <pre className="error-box">{state.error}</pre>
        <Button className="retry-button" onClick={onRetry}>
          Retry
        </Button>
      </div>
    );
  }

  if (state.data?.status === "failed") {
    return (
      <div>
        <pre className="error-box">{state.data.error_message ?? "Summary generation failed."}</pre>
        <Button className="retry-button" onClick={onRetry}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="content-block section-body">
      {state.data?.summary ? <p>{state.data.summary}</p> : <p>No summary available.</p>}
      <p className="muted-small">Source: {state.data?.source ?? "llm"}</p>
    </div>
  );
}
