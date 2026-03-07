import { YouTubeVideo } from "../../api";
import { VideoCard } from "./VideoCard";

type VideoGridProps = {
  videos: YouTubeVideo[];
  onOpen: (video: YouTubeVideo) => void;
};

export function VideoGrid({ videos, onOpen }: VideoGridProps) {
  return (
    <div className="video-grid">
      {videos.map((video) => (
        <VideoCard key={video.video_id} video={video} onOpen={onOpen} />
      ))}
    </div>
  );
}
