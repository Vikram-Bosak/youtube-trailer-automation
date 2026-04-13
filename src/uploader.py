"""
YouTube Uploader Module
Uploads processed trailer videos to YouTube using the YouTube Data API v3.
Handles OAuth2 authentication and respects daily upload limits.
"""

import logging
import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google.oauth2 import credentials as oauth_credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

import config

logger = logging.getLogger(__name__)


class YouTubeUploader:
    """Uploads videos to YouTube with OAuth2 authentication."""

    def __init__(self):
        self.youtube = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with YouTube using OAuth2."""
        creds = None
        token_path = Path(config.GOOGLE_OAUTH_TOKEN_FILE)
        secrets_path = Path(config.GOOGLE_CLIENT_SECRETS_FILE)

        # Check for existing token
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(token_path), config.YOUTUBE_SCOPES
                )
            except Exception as e:
                logger.warning(f"Error loading token: {e}")
                creds = None

        # Refresh token if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_credentials(creds, token_path)
                logger.info("Refreshed OAuth token")
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                creds = None

        # If no valid credentials, need to re-authenticate
        if not creds or not creds.valid:
            if secrets_path.exists():
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(secrets_path), config.YOUTUBE_SCOPES
                    )
                    creds = flow.run_local_server(port=8080)
                    self._save_credentials(creds, token_path)
                    logger.info("New OAuth token generated")
                except Exception as e:
                    logger.error(f"OAuth authentication failed: {e}")
                    return
            else:
                logger.error(
                    f"Client secrets file not found: {secrets_path}. "
                    "Run scripts/generate_oauth_token.py first!"
                )
                return

        # Build YouTube service
        try:
            self.youtube = build("youtube", "v3", credentials=creds)
            logger.info("YouTube API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to build YouTube service: {e}")

    def _save_credentials(self, creds, token_path: Path):
        """Save credentials to file."""
        import json
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes
        }
        with open(token_path, "w") as f:
            json.dump(token_data, f)

    def can_upload_today(self, state: dict) -> bool:
        """
        Check if we can upload today based on daily limit.
        
        Args:
            state: Application state dict
            
        Returns:
            True if we can upload more videos today
        """
        today = date.today().isoformat()
        last_upload_date = state.get("last_upload_date")

        if last_upload_date != today:
            # New day, reset counter
            state["daily_upload_count"] = 0
            state["last_upload_date"] = today
            config.save_state(state)

        count = state.get("daily_upload_count", 0)
        if count >= config.MAX_DAILY_UPLOADS:
            logger.info(
                f"Daily upload limit reached ({count}/{config.MAX_DAILY_UPLOADS})"
            )
            return False

        return True

    def is_upload_window(self) -> bool:
        """
        Check if current time is within an upload window.
        If UPLOAD_TIME_WINDOWS is empty or contains 0-23 all hours, uploads anytime (24/7).
        
        Returns:
            True if upload is allowed at current time
        """
        from datetime import timezone, timedelta

        # If no windows configured or all hours covered, allow 24/7
        windows = config.UPLOAD_TIME_WINDOWS
        if not windows or set(windows) == set(range(24)):
            logger.debug("Upload windows set to 24/7 mode - anytime upload allowed")
            return True

        # IST offset
        ist = timezone(timedelta(hours=5, minutes=30))
        current_hour = datetime.now(ist).hour

        if current_hour in windows:
            return True

        logger.info(
            f"Current hour {current_hour} IST is not in upload windows "
            f"{windows}. Next window: will retry in next cycle."
        )
        return False

    def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list,
        video_id: str = "",
    ) -> Optional[str]:
        """
        Upload a video to YouTube.
        
        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags
            video_id: Original video ID (for tracking)
            
        Returns:
            Uploaded video ID, or None if failed
        """
        if not self.youtube:
            logger.error("YouTube client not authenticated")
            return None

        if not video_path.exists():
            logger.error(f"Video file not found: {video_path}")
            return None

        try:
            # Prepare upload
            body = {
                "snippet": {
                    "title": title[:100],  # YouTube title limit
                    "description": description[:5000],  # YouTube description limit
                    "tags": tags[:500],  # YouTube tag limit
                    "categoryId": "1",  # Film & Animation
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                    "embeddable": True,
                    "license": "youtube",
                    "publicStatsViewable": True,
                },
            }

            media = MediaFileUpload(
                str(video_path),
                mimetype="video/mp4",
                resumable=True,
                chunksize=10 * 1024 * 1024,  # 10MB chunks
            )

            request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media,
            )

            # Upload with progress tracking
            logger.info(f"Uploading: {title}")
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.debug(f"Upload progress: {progress}%")

            uploaded_id = response["id"]
            uploaded_url = f"https://www.youtube.com/watch?v={uploaded_id}"
            logger.info(f"Upload successful! Video URL: {uploaded_url}")

            return uploaded_id

        except HttpError as e:
            if e.resp.status == 403:
                logger.error("Upload quota exceeded. Try again tomorrow.")
            elif e.resp.status == 400:
                logger.error(f"Bad request: {e}")
            else:
                logger.error(f"HTTP error during upload: {e}")
            return None
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            return None

    def upload_with_schedule(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list,
        state: dict,
        video_id: str = "",
    ) -> Optional[str]:
        """
        Upload a video respecting daily limits and time windows.
        
        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags
            state: Application state dict
            video_id: Original video ID
            
        Returns:
            Uploaded video ID, or None if failed/skipped
        """
        # Check daily limit
        if not self.can_upload_today(state):
            logger.warning("Daily upload limit reached, skipping")
            return None

        # Check upload window
        if not self.is_upload_window():
            logger.warning("Outside upload window, will retry later")
            return None

        # Upload
        result = self.upload(video_path, title, description, tags, video_id)

        if result:
            # Update state
            state["daily_upload_count"] = state.get("daily_upload_count", 0) + 1
            config.save_state(state)
            logger.info(
                f"Upload count today: {state['daily_upload_count']}/{config.MAX_DAILY_UPLOADS}"
            )

        return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uploader = YouTubeUploader()
    print(f"YouTube client ready: {uploader.youtube is not None}")
