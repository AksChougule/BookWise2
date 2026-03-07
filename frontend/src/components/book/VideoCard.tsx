import { YouTubeVideo } from "../../api";

type VideoCardProps = {
  video: YouTubeVideo;
  onOpen: (video: YouTubeVideo) => void;
};

export function VideoCard({ video, onOpen }: VideoCardProps) {
  return (
    <button type="button" className="video-card" onClick={() => onOpen(video)}>
      {video.thumbnail ? (
        <img src={video.thumbnail} alt={video.title} className="video-thumbnail" />
      ) : (
        <div className="video-thumbnail video-thumbnail-placeholder">No preview</div>
      )}
      <div className="video-body">
        <p className="video-title">{video.title}</p>
        <p className="video-meta">{video.channel}</p>
        <p className="video-meta">{video.views.toLocaleString()} views</p>
      </div>
    </button>
  );
}
