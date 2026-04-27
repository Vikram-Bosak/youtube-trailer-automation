"""
Downloader Module - Enhanced Version with Multiple Download Strategies
Downloads YouTube videos using yt-dlp with aggressive bypass options.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

import yt_dlp

import config

logger = logging.getLogger(__name__)

# List of public Invidious instances to use as fallback
INVIDIOUS_INSTANCES = [
    "https://yewtu.be",
    "https://vid.puffyan.us",
    "https://invidious.snopyta.org",
    "https://invidious.kavin.rocks",
    "https://inv.riverside.rocks",
    "https://invidious.osi.kr",
    "https://invidious.fdn.fr",
    "https://invidious.nerdvpn.de",
    "https://inv.bp.projectsegfau.lt",
]


class VideoDownloader:
    """Downloads YouTube videos using yt-dlp with multiple strategies."""

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
        Download a YouTube video with multiple strategies.
        
        Args:
            video_url: Full YouTube video URL
            video_id: YouTube video ID (used for filename)
            
        Returns:
            Path to downloaded file, or None if failed
        """
        output_template = str(self.download_dir / f"{video_id}.%(ext)s")

        # Strategy 1: Try Android client (most likely to work)
        logger.info("🎯 Strategy 1: Trying Android client...")
        result = self._download_with_android_client(video_url, video_id, output_template)
        if result:
            return result

        # Strategy 2: Try iOS client
        logger.info("🎯 Strategy 2: Trying iOS client...")
        result = self._download_with_ios_client(video_url, video_id, output_template)
        if result:
            return result

        # Strategy 3: Try Web client with cookies
        logger.info("🎯 Strategy 3: Trying Web client with cookies...")
        result = self._download_with_web_client(video_url, video_id, output_template)
        if result:
            return result

        # Strategy 4: Try Invidious instances
        logger.info("🎯 Strategy 4: Trying Invidious instances...")
        for instance in INVIDIOUS_INSTANCES:
            invidious_url = f"{instance}/watch?v={video_id}"
            logger.info(f"Trying Invidious instance: {instance}")
            result = self._download_with_invidious(invidious_url, video_id, output_template)
            if result:
                logger.info(f"✅ Successfully downloaded via Invidious: {instance}")
                return result

        # Strategy 5: Try subprocess with aggressive options
        logger.info("🎯 Strategy 5: Trying subprocess with aggressive options...")
        result = self._download_with_subprocess(video_url, video_id, output_template)
        if result:
            return result

        logger.error(f"❌ All download strategies failed for {video_id}")
        return None

    def _download_with_android_client(self, video_url: str, video_id: str, output_template: str) -> Optional[Path]:
        """Download using Android client (bypasses most restrictions)."""
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"],
                    "player_skip": ["configs", "js", "webpage"],
                }
            },
            "http_headers": {
                "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 12) gzip",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
            "retries": 10,
            "fragment_retries": 20,
            "file_access_retries": 10,
            "socket_timeout": 120,
            "ignoreerrors": False,
            "no_warnings": False,
            "noplaylist": True,
            "quiet": False,
            "no_color": True,
        }
        return self._execute_download(ydl_opts, video_url, video_id)

    def _download_with_ios_client(self, video_url: str, video_id: str, output_template: str) -> Optional[Path]:
        """Download using iOS client."""
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios"],
                    "player_skip": ["configs", "js", "webpage"],
                }
            },
            "http_headers": {
                "User-Agent": "com.google.ios.youtube/19.09.3 (iPhone14,3; U; CPU iOS 15_0 like Mac OS X)",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
            "retries": 10,
            "fragment_retries": 20,
            "file_access_retries": 10,
            "socket_timeout": 120,
            "ignoreerrors": False,
            "no_warnings": False,
            "noplaylist": True,
            "quiet": False,
            "no_color": True,
        }
        return self._execute_download(ydl_opts, video_url, video_id)

    def _download_with_web_client(self, video_url: str, video_id: str, output_template: str) -> Optional[Path]:
        """Download using Web client with cookies."""
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "cookiefile": self._find_cookie_file(),
            "extractor_args": {
                "youtube": {
                    "player_client": ["web"],
                }
            },
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "retries": 10,
            "fragment_retries": 20,
            "file_access_retries": 10,
            "socket_timeout": 120,
            "ignoreerrors": False,
            "no_warnings": False,
            "noplaylist": True,
            "quiet": False,
            "no_color": True,
        }
        return self._execute_download(ydl_opts, video_url, video_id)

    def _download_with_invidious(self, video_url: str, video_id: str, output_template: str) -> Optional[Path]:
        """Download using Invidious instance."""
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "retries": 10,
            "fragment_retries": 20,
            "file_access_retries": 10,
            "socket_timeout": 120,
            "ignoreerrors": False,
            "no_warnings": False,
            "noplaylist": True,
            "quiet": False,
            "no_color": True,
        }
        return self._execute_download(ydl_opts, video_url, video_id)

    def _download_with_subprocess(self, video_url: str, video_id: str, output_template: str) -> Optional[Path]:
        """Download using subprocess with aggressive options."""
        try:
            cmd = [
                "yt-dlp",
                "--format", "best[ext=mp4]/best",
                "--output", output_template,
                "--merge-output-format", "mp4",
                "--extractor-args", "youtube:player_client=android",
                "--extractor-args", "youtube:player_skip=configs,js,webpage",
                "--user-agent", "com.google.android.youtube/19.09.37 (Linux; U; Android 12) gzip",
                "--retries", "10",
                "--fragment-retries", "20",
                "--socket-timeout", "120",
                "--no-playlist",
                "--no-warnings",
                video_url
            ]
            
            # Add cookies if available
            cookie_file = self._find_cookie_file()
            if cookie_file:
                cmd.extend(["--cookies", cookie_file])
            
            logger.info(f"🚀 Running subprocess command: {' '.join(cmd[:5])}...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Subprocess download successful")
                # Find the downloaded file
                return self._find_downloaded_file(video_id)
            else:
                logger.error(f"❌ Subprocess download failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Subprocess download timed out")
            return None
        except Exception as e:
            logger.error(f"❌ Subprocess download error: {e}")
            return None

    def _execute_download(self, ydl_opts: dict, video_url: str, video_id: str) -> Optional[Path]:
        """Execute download with given options."""
        # Remove None options
        ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}

        try:
            logger.info(f"🎬 Starting download: {video_url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download
                info = ydl.extract_info(video_url, download=True)
                
                # Get the actual downloaded filename
                if info:
                    title = info.get("title", "Unknown")
                    duration = info.get("duration", 0)
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
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error downloading {video_id}: {e}")
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
        logger.info("🍪 No cookie file found")
        return None

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
            "extract_flat": False,
            "noplaylist": True,
        }
        
        # Try Android client first
        ydl_opts.update({
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"],
                    "player_skip": ["configs", "js", "webpage"],
                }
            },
            "http_headers": {
                "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 12) gzip",
            },
        })
        
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
