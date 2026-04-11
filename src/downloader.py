"""
Downloader Module
Downloads YouTube videos using yt-dlp.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import yt_dlp

import config

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Downloads YouTube videos using yt-dlp."""

    def __init__(self, download_dir: Optional[Path] = None):
        self.download_dir = download_dir or config.DOWNLOAD_DIR
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download(self, video_url: str, video_id: str) -> Optional[Path]:
        """
        Download a YouTube video.
        
        Args:
            video_url: Full YouTube video URL
            video_id: YouTube video ID (used for filename)
            
        Returns:
            Path to downloaded file, or None if failed
        """
        output_template = str(self.download_dir / f"{video_id}.%(ext)s")

        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                }
            ],
            # Progress hooks
            "progress_hooks": [self._progress_hook],
            # Retries
            "retries": 3,
            "fragment_retries": 3,
            # Skip errors
            "ignoreerrors": False,
            "no_warnings": True,
            # Cookie file for age-restricted videos
            "cookiefile": self._find_cookie_file(),
        }

        # Remove None options
        ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}

        try:
            logger.info(f"Downloading: {video_url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                
                # Get the actual downloaded filename
                if info:
                    duration = info.get("duration", 0)
                    title = info.get("title", "Unknown")
                    logger.info(f"Downloaded: {title} (Duration: {duration}s)")
                    
                    # Find the downloaded file
                    downloaded_path = self._find_downloaded_file(video_id)
                    if downloaded_path and downloaded_path.exists():
                        logger.info(f"File saved: {downloaded_path}")
                        return downloaded_path

            logger.error(f"Could not find downloaded file for {video_id}")
            return None

        except yt_dlp.DownloadError as e:
            logger.error(f"Download error for {video_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {video_id}: {e}")
            return None

    def _find_downloaded_file(self, video_id: str) -> Optional[Path]:
        """Find the downloaded file by video ID."""
        # yt-dlp might save as .mp4, .webm, .mkv etc.
        for ext in ["mp4", "webm", "mkv"]:
            path = self.download_dir / f"{video_id}.{ext}"
            if path.exists():
                return path

        # Check for .mp4 with additional suffix (from merging)
        for f in self.download_dir.iterdir():
            if f.stem.startswith(video_id) and f.suffix == ".mp4":
                return f

        return None

    def _find_cookie_file(self) -> Optional[str]:
        """Find cookies.txt file if it exists."""
        cookie_paths = [
            Path("cookies.txt"),
            Path(config.BASE_DIR / "cookies.txt"),
            Path(config.BASE_DIR / "data" / "cookies.txt"),
        ]
        for p in cookie_paths:
            if p.exists():
                logger.info(f"Using cookie file: {p}")
                return str(p)
        return None

    def _progress_hook(self, d):
        """Progress hook for yt-dlp downloads."""
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "N/A")
            speed = d.get("_speed_str", "N/A")
            logger.debug(f"Download progress: {percent} at {speed}")
        elif d["status"] == "finished":
            logger.info("Download finished, processing...")

    def get_video_info(self, video_url: str) -> Optional[dict]:
        """
        Get video info without downloading.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Video info dict or None
        """
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "cookiefile": self._find_cookie_file(),
        }
        ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(video_url, download=False)
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None

    def cleanup(self, video_id: str):
        """Remove downloaded file after processing."""
        for ext in ["mp4", "webm", "mkv"]:
            path = self.download_dir / f"{video_id}.{ext}"
            if path.exists():
                path.unlink()
                logger.info(f"Cleaned up: {path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    downloader = VideoDownloader()
    # Test download
    result = downloader.download("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "test")
    print(f"Result: {result}")
