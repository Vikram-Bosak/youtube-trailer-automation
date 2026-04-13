"""
Trailer Detector Module
Monitors YouTube channels for new trailer uploads.
Uses YouTube Data API v3 to search for new videos.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

logger = logging.getLogger(__name__)

# Keywords to identify trailers
TRAILER_KEYWORDS = [
    "trailer", "official trailer", "teaser", "teaser trailer",
    "first look", "preview", "official preview",
    "official video", "official", "in theaters", "coming soon",
    "tickets on sale", "in cinemas", "only in theaters",
    "only in cinemas", "in theaters and imax", "watch the",
    "get your tickets", "now playing", "this summer",
    "this friday", "soon", "new look", "sneak peek"
]

# Keywords to exclude (these are NOT trailers)
EXCLUDE_KEYWORDS = [
    "reaction", "review", "breakdown", "analysis", "explained",
    "fan made", "fan-made", "concept", "recap", "summary",
    "full movie", "full episode", "gameplay", "behind the scenes",
    "bts", "making of", "interview", "featurette",
    "vlog", "podcast", "livestream", "live stream",
    "tutorial", "how to", "top 10", "ranking",
    "viralshorts", "shorts", "viral"
]

# Channels where ALL new videos are treated as trailers (official studio channels)
AUTO_TRAILER_CHANNELS = set()  # Will be populated from config


class TrailerDetector:
    """Detects new trailer videos from monitored YouTube channels."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the detector.
        
        Args:
            api_key: YouTube Data API key. Uses config.YOUTUBE_API_KEY if not provided.
        """
        self.api_key = api_key or config.YOUTUBE_API_KEY
        self.youtube = None
        if self.api_key:
            try:
                self.youtube = build("youtube", "v3", developerKey=self.api_key)
                logger.info("YouTube Data API client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize YouTube API client: {e}")

        # All monitored channels are treated as official studio channels
        # So ALL their new videos are treated as trailers/promos
        global AUTO_TRAILER_CHANNELS
        AUTO_TRAILER_CHANNELS = set(config.MONITORED_CHANNEL_IDS)
        logger.info(f"Auto-trailer channels: {len(AUTO_TRAILER_CHANNELS)} channels")

    def get_channel_uploads_playlist(self, channel_id: str) -> Optional[str]:
        """Get the uploads playlist ID for a channel."""
        if not self.youtube:
            return None
        try:
            request = self.youtube.channels().list(
                part="contentDetails",
                id=channel_id
            )
            response = request.execute()
            if response["items"]:
                return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        except HttpError as e:
            logger.error(f"Error getting uploads playlist for {channel_id}: {e}")
        return None

    def _get_video_durations(self, video_ids: List[str]) -> dict:
        """
        Get duration for multiple videos using YouTube Data API.
        Returns dict mapping video_id -> duration_str (e.g. 'PT2M30S')
        """
        if not self.youtube or not video_ids:
            return {}
        durations = {}
        try:
            # Process in batches of 50 (API limit)
            for i in range(0, len(video_ids), 50):
                batch = video_ids[i:i+50]
                request = self.youtube.videos().list(
                    part="contentDetails",
                    id=",".join(batch)
                )
                response = request.execute()
                for item in response.get("items", []):
                    vid_id = item["id"]
                    duration = item.get("contentDetails", {}).get("duration", "")
                    durations[vid_id] = duration
        except HttpError as e:
            logger.error(f"Error fetching video durations: {e}")
        return durations

    def _parse_duration(self, duration_str: str) -> int:
        """
        Parse ISO 8601 duration (PT2M30S) to seconds.
        """
        import re
        if not duration_str:
            return 0
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds

    def _is_short(self, duration_str: str) -> bool:
        """
        Check if a video is a YouTube Short (under 60 seconds).
        """
        return self._parse_duration(duration_str) < 60

    def get_latest_videos_api(self, channel_id: str, hours: int = 24) -> List[dict]:
        """
        Get latest videos from a channel using YouTube Data API.
        Filters out YouTube Shorts (videos under 60 seconds).
        
        Args:
            channel_id: YouTube channel ID
            hours: Look back period in hours
            
        Returns:
            List of video info dicts (LONG videos only, no Shorts)
        """
        if not self.youtube:
            logger.warning("YouTube API client not available, using RSS fallback")
            return self.get_latest_videos_rss(channel_id, hours)

        videos = []
        try:
            playlist_id = self.get_channel_uploads_playlist(channel_id)
            if not playlist_id:
                logger.error(f"Could not get uploads playlist for channel {channel_id}")
                return videos

            cutoff = datetime.utcnow() - timedelta(hours=hours)

            request = self.youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=10
            )
            response = request.execute()

            # Collect all videos first
            raw_videos = []
            for item in response.get("items", []):
                snippet = item["snippet"]
                published_at = datetime.strptime(
                    snippet["publishedAt"], "%Y-%m-%dT%H:%M:%S%z"
                ).replace(tzinfo=None)

                if published_at < cutoff:
                    continue

                video_info = {
                    "video_id": snippet["resourceId"]["videoId"],
                    "title": snippet["title"],
                    "channel_id": channel_id,
                    "channel_title": snippet["channelTitle"],
                    "published_at": snippet["publishedAt"],
                    "description": snippet.get("description", ""),
                    "thumbnail": snippet["thumbnails"].get("high", {}).get("url", ""),
                    "url": f"https://www.youtube.com/watch?v={snippet['resourceId']['videoId']}"
                }
                raw_videos.append(video_info)

            # Filter out Shorts - get durations for all videos
            if raw_videos:
                video_ids = [v["video_id"] for v in raw_videos]
                durations = self._get_video_durations(video_ids)

                for video in raw_videos:
                    vid_id = video["video_id"]
                    duration_str = durations.get(vid_id, "")

                    if self._is_short(duration_str):
                        duration_sec = self._parse_duration(duration_str)
                        logger.info(f"SKIP SHORT: {video['title']} ({duration_sec}s)")
                        continue

                    # Store duration info
                    video["duration"] = duration_str
                    video["duration_seconds"] = self._parse_duration(duration_str)
                    videos.append(video)
                    logger.debug(f"LONG VIDEO: {video['title']} ({video['duration_seconds']}s)")

        except HttpError as e:
            logger.error(f"Error fetching videos from {channel_id}: {e}")

        return videos

    def get_latest_videos_rss(self, channel_id: str, hours: int = 24) -> List[dict]:
        """
        Get latest videos from a channel using RSS feed.
        Fallback method that doesn't require API key.
        
        Args:
            channel_id: YouTube channel ID
            hours: Look back period in hours
            
        Returns:
            List of video info dicts
        """
        import feedparser
        from dateutil import parser as date_parser

        videos = []
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

        try:
            feed = feedparser.parse(rss_url)
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            for entry in feed.entries:
                published = date_parser.parse(entry.published).replace(tzinfo=None)
                if published < cutoff:
                    continue

                video_id = entry.yt_videoid if hasattr(entry, 'yt_videoid') else entry.link.split("v=")[-1]

                video_info = {
                    "video_id": video_id,
                    "title": entry.title,
                    "channel_id": channel_id,
                    "channel_title": entry.author if hasattr(entry, 'author') else "",
                    "published_at": entry.published,
                    "description": entry.summary if hasattr(entry, 'summary') else "",
                    "thumbnail": entry.media_thumbnail[0]["url"] if hasattr(entry, 'media_thumbnail') else "",
                    "url": f"https://www.youtube.com/watch?v={video_id}"
                }
                videos.append(video_info)

        except Exception as e:
            logger.error(f"Error fetching RSS feed for {channel_id}: {e}")

        return videos

    def is_trailer(self, video_info: dict) -> bool:
        """
        Check if a video is a trailer based on title, description, and channel.
        
        Args:
            video_info: Video information dict
            
        Returns:
            True if the video appears to be a trailer
        """
        title = video_info.get("title", "").lower()
        description = video_info.get("description", "").lower()
        channel_id = video_info.get("channel_id", "")
        combined = f"{title} {description}"

        # Check for exclusion keywords FIRST - these are definitely NOT trailers
        has_exclude_keyword = any(
            kw in combined for kw in EXCLUDE_KEYWORDS
        )
        if has_exclude_keyword:
            return False

        # If this is an official studio channel, treat ALL videos as trailers
        # (Studio channels only post promotional content)
        if channel_id in AUTO_TRAILER_CHANNELS:
            logger.debug(f"Auto-accepting from studio channel: {title}")
            return True

        # Check for trailer keywords
        has_trailer_keyword = any(
            kw in combined for kw in TRAILER_KEYWORDS
        )

        # Video duration check - trailers are typically 1-5 minutes
        # This will be refined after download when we know actual duration
        
        return has_trailer_keyword

    def find_reuploaders(self, video_info: dict, max_results: int = 5) -> List[dict]:
        """
        Search YouTube for other channels that uploaded the same trailer.
        
        Args:
            video_info: Original video info dict
            max_results: Maximum number of re-uploaders to return
            
        Returns:
            List of re-uploader dicts with channel_title, url, published_at
        """
        if not self.youtube:
            logger.warning("YouTube API client not available, cannot find re-uploaders")
            return []

        original_video_id = video_info.get("video_id", "")
        title = video_info.get("title", "")
        
        # Extract a clean search query from the title
        import re
        # Remove special chars, keep alphanumeric and spaces
        search_query = re.sub(r'[^\w\s]', ' ', title)
        # Remove extra spaces
        search_query = ' '.join(search_query.split())
        
        if not search_query:
            return []

        reuploaders = []
        try:
            request = self.youtube.search().list(
                part="snippet",
                q=search_query,
                type="video",
                maxResults=max_results + 5,  # Get extra to filter out original
                order="relevance",
                publishedAfter=(
                    datetime.utcnow() - timedelta(days=7)
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            response = request.execute()

            for item in response.get("items", []):
                vid_id = item["id"].get("videoId", "")
                
                # Skip the original video itself
                if vid_id == original_video_id:
                    continue
                
                # Skip if same channel as original
                channel_id = item["snippet"].get("channelId", "")
                original_channel = video_info.get("channel_id", "")
                if channel_id and channel_id == original_channel:
                    continue

                reuploader = {
                    "channel_title": item["snippet"]["channelTitle"],
                    "video_id": vid_id,
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                    "published_at": item["snippet"]["publishedAt"],
                    "title": item["snippet"]["title"],
                    "thumbnail": item["snippet"]["thumbnails"].get("high", {}).get("url", ""),
                }
                reuploaders.append(reuploader)
                
                if len(reuploaders) >= max_results:
                    break

        except HttpError as e:
            logger.error(f"Error searching for re-uploaders: {e}")

        return reuploaders

    def detect_new_trailers(self, hours: int = 24, processed_ids: set = None) -> List[dict]:
        """
        Scan all monitored channels for new trailers.
        
        Args:
            hours: Look back period in hours
            processed_ids: Set of already processed video IDs to skip
            
        Returns:
            List of new trailer video info dicts
        """
        if processed_ids is None:
            processed_ids = set()

        new_trailers = []

        for channel_id in config.MONITORED_CHANNEL_IDS:
            logger.info(f"Scanning channel {channel_id} for new trailers...")

            # Try API first, fall back to RSS
            if self.youtube:
                videos = self.get_latest_videos_api(channel_id, hours)
            else:
                videos = self.get_latest_videos_rss(channel_id, hours)

            for video in videos:
                video_id = video["video_id"]

                # Skip already processed videos
                if video_id in processed_ids:
                    continue

                # Check if it's a trailer
                if self.is_trailer(video):
                    logger.info(f"Found new trailer: {video['title']} ({video_id})")
                    new_trailers.append(video)
                else:
                    logger.debug(f"Skipping non-trailer: {video['title']} ({video_id})")

        logger.info(f"Total new trailers found: {len(new_trailers)}")
        return new_trailers


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    detector = TrailerDetector()
    trailers = detector.detect_new_trailers()
    for t in trailers:
        print(f"🎬 {t['title']}")
        print(f"   URL: {t['url']}")
        print(f"   Channel: {t['channel_title']}")
        print()
