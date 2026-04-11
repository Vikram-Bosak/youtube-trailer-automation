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
    "first look", "preview", "official preview"
]

# Keywords to exclude
EXCLUDE_KEYWORDS = [
    "reaction", "review", "breakdown", "analysis", "explained",
    "fan made", "fan-made", "concept", "recap", "summary"
]


class TrailerDetector:
    """Detects new trailer videos from monitored YouTube channels."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the detector.
        
        Args:
            api_key: YouTube Data API key. Uses GEMINI_API_KEY or config if not provided.
                     Note: For channel monitoring, we can also use yt-dlp RSS feeds
                     which don't require API key.
        """
        self.api_key = api_key
        self.youtube = None
        if self.api_key:
            try:
                self.youtube = build("youtube", "v3", developerKey=self.api_key)
                logger.info("YouTube Data API client initialized")
            except Exception as e:
                logger.warning(f"Failed to init YouTube API client: {e}")

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

    def get_latest_videos_api(self, channel_id: str, hours: int = 24) -> List[dict]:
        """
        Get latest videos from a channel using YouTube Data API.
        
        Args:
            channel_id: YouTube channel ID
            hours: Look back period in hours
            
        Returns:
            List of video info dicts
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
                    "channel_title": snippet["channelTitle"],
                    "published_at": snippet["publishedAt"],
                    "description": snippet.get("description", ""),
                    "thumbnail": snippet["thumbnails"].get("high", {}).get("url", ""),
                    "url": f"https://www.youtube.com/watch?v={snippet['resourceId']['videoId']}"
                }
                videos.append(video_info)

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
        Check if a video is a trailer based on title and description.
        
        Args:
            video_info: Video information dict
            
        Returns:
            True if the video appears to be a trailer
        """
        title = video_info.get("title", "").lower()
        description = video_info.get("description", "").lower()
        combined = f"{title} {description}"

        # Check for trailer keywords
        has_trailer_keyword = any(
            kw in combined for kw in TRAILER_KEYWORDS
        )

        # Check for exclusion keywords
        has_exclude_keyword = any(
            kw in combined for kw in EXCLUDE_KEYWORDS
        )

        # Video duration check - trailers are typically 1-5 minutes
        # This will be refined after download when we know actual duration
        
        return has_trailer_keyword and not has_exclude_keyword

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
