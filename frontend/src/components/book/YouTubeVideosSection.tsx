import { YouTubeVideo, YouTubeVideosResponse } from "../../api";
import { VideoGrid } from "./VideoGrid";

type SectionState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

type YouTubeVideosSectionProps = {
  state: SectionState<YouTubeVideosResponse>;
  onOpenVideo: (video: YouTubeVideo) => void;
};

export function YouTubeVideosSection({ state, onOpenVideo }: YouTubeVideosSectionProps) {
  if (state.loading) {
    return (
      <div className="placeholder">
        <p>Loading related videos…</p>
        <p className="muted-small">Please wait while we fetch the best matches.</p>
      </div>
    );
  }

  if (state.error) {
    return <pre className="error-box">{state.error}</pre>;
  }

  if (!state.data || state.data.videos.length === 0) {
    return <p className="placeholder-copy">No videos available yet.</p>;
  }

  return (
    <div className="section-body">
      <p className="muted-small">Source: {state.data.source}</p>
      <VideoGrid videos={state.data.videos} onOpen={onOpenVideo} />
    </div>
  );
}
