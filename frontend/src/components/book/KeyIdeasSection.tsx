import { KeyIdeasResponse } from "../../api";
import { Button } from "../ui/button";

type KeyIdeasSectionProps = {
  state: {
    data: KeyIdeasResponse | null;
    loading: boolean;
    error: string | null;
  };
  onRetry: () => void;
};

export function KeyIdeasSection({ state, onRetry }: KeyIdeasSectionProps) {
  if (state.loading) {
    return (
      <div className="skeleton">
        <div className="line" />
        <div className="line short" />
        <p>Loading key ideas…</p>
      </div>
    );
  }

  if (state.error || state.data?.status === "failed") {
    return (
      <div>
        <pre className="error-box">{state.error ?? state.data?.error_message ?? "Key ideas generation failed."}</pre>
        <Button className="retry-button" onClick={onRetry}>
          Retry
        </Button>
      </div>
    );
  }

  return <pre className="content-box">{state.data?.key_ideas ?? "No key ideas available."}</pre>;
}
