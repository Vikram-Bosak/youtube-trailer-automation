"""
Telegram Report Module
Sends notifications and reports via Telegram bot.
"""

import logging
from datetime import datetime
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)


class TelegramReporter:
    """Sends notifications and reports via Telegram."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        self.bot_token = bot_token or config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def _send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message via Telegram bot.
        
        Args:
            text: Message text (supports HTML formatting)
            parse_mode: Parse mode (HTML or Markdown)
            
        Returns:
            True if message sent successfully
        """
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not configured, skipping notification")
            return False

        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }

            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                logger.debug("Telegram message sent successfully")
                return True
            else:
                logger.error(
                    f"Telegram API error: {response.status_code} - {response.text}"
                )
                return False

        except requests.exceptions.Timeout:
            logger.error("Telegram request timed out")
            return False
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def send_trailer_detected(self, video_info: dict) -> bool:
        """
        Send notification when a new trailer is detected.
        
        Args:
            video_info: Video info dict from detector
            
        Returns:
            True if message sent successfully
        """
        message = (
            f"🎬 <b>New Trailer Detected!</b>\n\n"
            f"📹 <b>Title:</b> {video_info.get('title', 'Unknown')}\n"
            f"📺 <b>Channel:</b> {video_info.get('channel_title', 'Unknown')}\n"
            f"🔗 <b>URL:</b> {video_info.get('url', 'N/A')}\n"
            f"📅 <b>Published:</b> {video_info.get('published_at', 'N/A')}\n\n"
            f"⏳ Processing will begin shortly..."
        )
        return self._send_message(message)

    def send_processing_complete(
        self, video_info: dict, processed_path: str
    ) -> bool:
        """
        Send notification when video processing is complete.
        
        Args:
            video_info: Video info dict
            processed_path: Path to processed file
            
        Returns:
            True if message sent successfully
        """
        message = (
            f"✅ <b>Processing Complete!</b>\n\n"
            f"📹 <b>Title:</b> {video_info.get('title', 'Unknown')}\n"
            f"📁 <b>File:</b> {processed_path}\n\n"
            f"📤 Ready for upload..."
        )
        return self._send_message(message)

    def send_upload_success(
        self, video_info: dict, uploaded_url: str, seo_data: dict
    ) -> bool:
        """
        Send notification when upload is successful.
        
        Args:
            video_info: Video info dict
            uploaded_url: URL of uploaded video
            seo_data: SEO content used
            
        Returns:
            True if message sent successfully
        """
        message = (
            f"🚀 <b>Upload Successful!</b>\n\n"
            f"📹 <b>Title:</b> {seo_data.get('title', 'Unknown')}\n"
            f"🔗 <b>Uploaded URL:</b> {uploaded_url}\n"
            f"📺 <b>Original:</b> {video_info.get('url', 'N/A')}\n"
            f"🏷️ <b>Tags:</b> {', '.join(seo_data.get('tags', [])[:5])}...\n\n"
            f"✅ Trailer re-uploaded successfully!"
        )
        return self._send_message(message)

    def send_upload_failed(self, video_info: dict, error: str) -> bool:
        """
        Send notification when upload fails.
        
        Args:
            video_info: Video info dict
            error: Error message
            
        Returns:
            True if message sent successfully
        """
        message = (
            f"❌ <b>Upload Failed!</b>\n\n"
            f"📹 <b>Title:</b> {video_info.get('title', 'Unknown')}\n"
            f"🔗 <b>URL:</b> {video_info.get('url', 'N/A')}\n"
            f"⚠️ <b>Error:</b> {error}\n\n"
            f"Will retry in next cycle."
        )
        return self._send_message(message)

    def send_daily_summary(self, stats: dict) -> bool:
        """
        Send daily summary report.
        
        Args:
            stats: Statistics dict with keys:
                - detected: Number of trailers detected
                - uploaded: Number of trailers uploaded
                - failed: Number of uploads failed
                - skipped: Number of trailers skipped (limit reached)
            
        Returns:
            True if message sent successfully
        """
        today = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = (
            f"📊 <b>Daily Summary Report</b>\n"
            f"📅 {today}\n\n"
            f"🎬 Trailers Detected: <b>{stats.get('detected', 0)}</b>\n"
            f"✅ Successfully Uploaded: <b>{stats.get('uploaded', 0)}</b>\n"
            f"❌ Failed Uploads: <b>{stats.get('failed', 0)}</b>\n"
            f"⏭️ Skipped (limit reached): <b>{stats.get('skipped', 0)}</b>\n\n"
            f"📈 Upload Quota: {stats.get('uploaded', 0)}/{config.MAX_DAILY_UPLOADS}"
        )
        return self._send_message(message)

    def send_error(self, error_message: str, context: str = "") -> bool:
        """
        Send error notification.
        
        Args:
            error_message: Error message
            context: Additional context
            
        Returns:
            True if message sent successfully
        """
        message = (
            f"🚨 <b>Error!</b>\n\n"
            f"⚠️ {error_message}\n"
        )
        if context:
            message += f"📋 <b>Context:</b> {context}"
        return self._send_message(message)

    def send_startup_message(self) -> bool:
        """
        Send notification when the automation starts.
        
        Returns:
            True if message sent successfully
        """
        message = (
            f"🤖 <b>YouTube Trailer Automation Started!</b>\n\n"
            f"👀 Monitoring {len(config.MONITORED_CHANNEL_IDS)} channel(s)\n"
            f"📤 Max daily uploads: {config.MAX_DAILY_UPLOADS}\n"
            f"🕐 Upload windows: {config.UPLOAD_TIME_WINDOWS} IST\n"
            f"🔄 Check interval: Every 30 minutes\n\n"
            f"✅ Ready to detect and re-upload trailers!"
        )
        return self._send_message(message)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reporter = TelegramReporter()
    reporter.send_startup_message()
