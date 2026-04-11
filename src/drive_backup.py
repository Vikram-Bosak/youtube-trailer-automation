"""
Google Drive Backup Module
Backs up processed videos and metadata to Google Drive.
"""

import logging
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

import config

logger = logging.getLogger(__name__)


class DriveBackup:
    """Backs up files to Google Drive."""

    def __init__(self):
        self.drive = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Drive using OAuth2."""
        creds = None
        token_path = Path(config.GOOGLE_OAUTH_TOKEN_FILE)
        secrets_path = Path(config.GOOGLE_CLIENT_SECRETS_FILE)

        # Check for existing token
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(token_path),
                    config.YOUTUBE_SCOPES + config.DRIVE_SCOPES
                )
            except Exception as e:
                logger.warning(f"Error loading token: {e}")
                creds = None

        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Refreshed Drive OAuth token")
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                creds = None

        # Need new credentials
        if not creds or not creds.valid:
            if secrets_path.exists():
                try:
                    all_scopes = config.YOUTUBE_SCOPES + config.DRIVE_SCOPES
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(secrets_path), all_scopes
                    )
                    creds = flow.run_local_server(port=8080)
                    logger.info("New OAuth token generated for Drive")
                except Exception as e:
                    logger.error(f"Drive OAuth failed: {e}")
                    return
            else:
                logger.error("Client secrets file not found")
                return

        # Build Drive service
        try:
            self.drive = build("drive", "v3", credentials=creds)
            logger.info("Google Drive API client initialized")
        except Exception as e:
            logger.error(f"Failed to build Drive service: {e}")

    def upload_file(
        self,
        file_path: Path,
        folder_id: Optional[str] = None,
        description: str = "",
    ) -> Optional[str]:
        """
        Upload a file to Google Drive.
        
        Args:
            file_path: Local path to the file
            folder_id: Google Drive folder ID (uses config default if None)
            description: File description
            
        Returns:
            Google Drive file ID, or None if failed
        """
        if not self.drive:
            logger.error("Drive client not authenticated")
            return None

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        folder_id = folder_id or config.GOOGLE_DRIVE_FOLDER_ID
        if not folder_id:
            logger.warning("No Google Drive folder ID configured, skipping backup")
            return None

        try:
            file_metadata = {
                "name": file_path.name,
                "description": description,
            }

            # Only add parents if folder_id is set
            if folder_id:
                file_metadata["parents"] = [folder_id]

            media = MediaFileUpload(
                str(file_path),
                mimetype="video/mp4" if file_path.suffix == ".mp4" else "application/octet-stream",
                resumable=True,
                chunksize=10 * 1024 * 1024,  # 10MB chunks
            )

            request = self.drive.files().create(
                body=file_metadata,
                media_body=media,
                fields="id,webViewLink",
            )

            logger.info(f"Backing up to Drive: {file_path.name}")
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.debug(f"Drive upload progress: {progress}%")

            file_id = response.get("id")
            web_link = response.get("webViewLink", "")
            logger.info(f"Drive backup successful! Link: {web_link}")

            return file_id

        except HttpError as e:
            logger.error(f"Drive upload error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error backing up to Drive: {e}")
            return None

    def upload_metadata(self, video_id: str, metadata: dict) -> Optional[str]:
        """
        Upload a JSON metadata file to Google Drive.
        
        Args:
            video_id: Video ID
            metadata: Metadata dict to save
            
        Returns:
            Google Drive file ID, or None if failed
        """
        import json
        import tempfile

        try:
            # Write metadata to temp file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump(metadata, f, indent=2)
                temp_path = Path(f.name)

            result = self.upload_file(
                temp_path,
                description=f"Metadata for video {video_id}"
            )

            # Cleanup temp file
            temp_path.unlink(missing_ok=True)

            return result

        except Exception as e:
            logger.error(f"Error uploading metadata: {e}")
            return None

    def file_exists(self, filename: str, folder_id: Optional[str] = None) -> bool:
        """
        Check if a file already exists in the Drive folder.
        
        Args:
            filename: Filename to check
            folder_id: Google Drive folder ID
            
        Returns:
            True if file exists
        """
        if not self.drive:
            return False

        folder_id = folder_id or config.GOOGLE_DRIVE_FOLDER_ID
        if not folder_id:
            return False

        try:
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            results = self.drive.files().list(
                q=query, spaces="drive", fields="files(id, name"
            ).execute()
            return len(results.get("files", [])) > 0
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    backup = DriveBackup()
    print(f"Drive client ready: {backup.drive is not None}")
