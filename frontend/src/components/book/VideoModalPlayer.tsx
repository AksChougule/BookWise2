import { useEffect } from "react";

import { YouTubeVideo } from "../../api";

type VideoModalPlayerProps = {
  video: YouTubeVideo | null;
  onClose: () => void;
};

export function VideoModalPlayer({ video, onClose }: VideoModalPlayerProps) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  if (!video) {
    return null;
  }

  return (
    <div className="video-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="video-modal"
        role="dialog"
        aria-modal="true"
        aria-label={video.title}
        onClick={(event) => event.stopPropagation()}
      >
        <button type="button" className="video-modal-close" onClick={onClose} aria-label="Close video player">
          Close
        </button>
        <div className="video-embed-wrap">
          <iframe
            src={`https://www.youtube.com/embed/${video.video_id}?autoplay=1`}
            title={video.title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            referrerPolicy="strict-origin-when-cross-origin"
            allowFullScreen
          />
        </div>
      </div>
    </div>
  );
}
