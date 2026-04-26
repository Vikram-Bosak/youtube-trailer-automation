"""
Downloader Module - Enhanced Version
Downloads YouTube videos using yt-dlp with better error handling and logging.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

import yt_dlp

import config

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Downloads YouTube videos using yt-dlp with enhanced error handling."""

    def __init__(self, download_dir: Optional[Path] = None):
        self.download_dir = download_dir or config.DOWNLOAD_DIR
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Check yt-dlp version
        self._check_yt_dlp_version()

    def _check_yt_dlp_version(self):
        """Check and log yt-dlp version."""
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            version = result.stdout.strip()
            logger.info(f"yt-dlp version: {version}")
        except Exception as e:
            logger.warning(f"Could not check yt-dlp version: {e}")

    def download(self, video_url: str, video_id: str) -> Optional[Path]:
        """
        Download a YouTube video with enhanced error handling.
        
        Args:
            video_url: Full YouTube video URL
            video_id: YouTube video ID (used for filename)
            
        Returns:
            Path to downloaded file, or None if failed
        """
        output_template = str(self.download_dir / f"{video_id}.%(ext)s")

        # Enhanced yt-dlp options
        ydl_opts = {
            # Format selection with fallbacks
            "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            
            # Post-processors
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                }
            ],
            
            # Progress hooks
            "progress_hooks": [self._progress_hook],
            
            # Retry logic
            "retries": 5,
            "fragment_retries": 10,
            "file_access_retries": 5,
            
            # Timeout settings
            "socket_timeout": 60,
            
            # Skip errors
            "ignoreerrors": False,
            "no_warnings": False,  # Enable warnings for debugging
            
            # Cookie file for age-restricted videos
            "cookiefile": self._find_cookie_file(),
            
            # User agent to avoid blocking
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            
            # Extract flat info first (faster)
            "extract_flat": False,
            
            # No playlist
            "noplaylist": True,
            
            # Quiet mode
            "quiet": False,
            "no_color": True,
        }

        # Remove None options
        ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}

        try:
            logger.info(f"🎬 Starting download: {video_url}")
            logger.info(f"📁 Output template: {output_template}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # First, try to get info without downloading
                try:
                    info = ydl.extract_info(video_url, download=False)
                    if info:
                        title = info.get("title", "Unknown")
                        duration = info.get("duration", 0)
                        logger.info(f"📹 Video info: {title} ({duration}s)")
                except Exception as e:
                    logger.warning(f"Could not get video info: {e}")
                
                # Now download
                info = ydl.extract_info(video_url, download=True)
                
                # Get the actual downloaded filename
                if info:
                    duration = info.get("duration", 0)
                    title = info.get("title", "Unknown")
                    logger.info(f"✅ Downloaded: {title} (Duration: {duration}s)")
                    
                    # Find the downloaded file
                    downloaded_path = self._find_downloaded_file(video_id)
                    if downloaded_path and downloaded_path.exists():
                        file_size = downloaded_path.stat().st_size / (1024 * 1024)  # MB
                        logger.info(f"📁 File saved: {downloaded_path} ({file_size:.2f} MB)")
                        return downloaded_path

            logger.error(f"❌ Could not find downloaded file for {video_id}")
            return None

        except yt_dlp.DownloadError as e:
            logger.error(f"❌ Download error for {video_id}: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error downloading {video_id}: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return None

    def _find_downloaded_file(self, video_id: str) -> Optional[Path]:
        """Find the downloaded file by video ID."""
        # Check common extensions
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
                logger.info(f"🍪 Using cookie file: {p}")
                return str(p)
        logger.info("🍪 No cookie file found (age-restricted videos may fail)")
        return None

    def _progress_hook(self, d):
        """Progress hook for yt-dlp downloads."""
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "N/A")
            speed = d.get("_speed_str", "N/A")
            eta = d.get("_eta_str", "N/A")
            logger.info(f"⬇️  Download: {percent} | Speed: {speed} | ETA: {eta}")
        elif d["status"] == "finished":
            logger.info("✅ Download finished, processing...")

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
                logger.info(f"🗑️  Cleaned up: {path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    downloader = VideoDownloader()
    # Test download
    result = downloader.download("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "test")
    print(f"Result: {result}")
