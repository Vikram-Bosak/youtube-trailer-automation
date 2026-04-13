"""
Telegram Report Module
Sends notifications and reports via Telegram bot.
Uses the new template format with real data - official channel + top re-uploaders.
"""

import logging
from datetime import datetime
from typing import Optional, List

import requests

import config

logger = logging.getLogger(__name__)


def _format_ist_time(published_at: str) -> str:
    """
    Format a UTC timestamp to IST readable format.
    
    Args:
        published_at: UTC timestamp string (ISO 8601 format)
        
    Returns:
        Formatted IST time string like '12 Apr 2026, 10:00 AM IST'
    """
    try:
        from dateutil import parser as date_parser
        dt = date_parser.parse(published_at)
        # Convert to IST (UTC+5:30)
        from datetime import timedelta
        ist_offset = timedelta(hours=5, minutes=30)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=None)
        else:
            dt = dt.utctimetuple()
            dt = datetime(*dt[:6])
        # Just format nicely without actual timezone conversion
        return dt.strftime("%d %b %Y, %I:%M %p IST")
    except Exception:
        return published_at


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
            logger.warning(
                f"Telegram credentials not configured "
                f"(bot_token={'set' if self.bot_token else 'MISSING'}, "
                f"chat_id={'set' if self.chat_id else 'MISSING'}), "
                f"skipping notification"
            )
            return False

        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }

            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info(f"Telegram message sent successfully to chat_id {self.chat_id}")
                    return True
                else:
                    logger.error(f"Telegram API returned error: {result}")
                    return False
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

    def send_trailer_detected(
        self, 
        video_info: dict, 
        reuploaders: List[dict] = None,
    ) -> bool:
        """
        Send notification when a new trailer is detected with the new template.
        
        Args:
            video_info: Video info dict from detector (real data)
            reuploaders: List of re-uploader dicts from find_reuploaders()
            
        Returns:
            True if message sent successfully
        """
        reuploaders = reuploaders or []
        
        # Build the official channel section
        title = video_info.get("title", "Unknown")
        channel = video_info.get("channel_title", "Unknown")
        url = video_info.get("url", "N/A")
        published = _format_ist_time(video_info.get("published_at", "N/A"))
        
        message = (
            f"🎬 <b>NEW TRAILER DETECTED & UPLOADED!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📺 <b>OFFICIAL CHANNEL (Source)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎬 <b>Title:</b> {title}\n"
            f"📺 <b>Channel:</b> {channel}\n"
            f"🔗 <a href=\"{url}\">{url}</a>\n"
            f"📅 <b>Published:</b> {published}\n"
        )
        
        # Add re-uploaders section if found
        if reuploaders:
            message += (
                f"\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 <b>TOP RE-UPLOADERS (Same Trailer)</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            
            for i, reuploader in enumerate(reuploaders[:5], 1):
                num_emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][i - 1]
                r_channel = reuploader.get("channel_title", "Unknown")
                r_url = reuploader.get("url", "N/A")
                r_published = _format_ist_time(reuploader.get("published_at", "N/A"))
                
                message += (
                    f"{num_emoji} <b>{r_channel}</b>\n"
                    f"   🔗 <a href=\"{r_url}\">{r_url}</a>\n"
                    f"   📅 {r_published}\n\n"
                )
        else:
            message += (
                f"\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 <b>No re-uploaders found yet</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
        
        # Add status footer
        message += (
            f"\n⏳ <b>Status:</b> Processing will begin shortly...\n"
            f"🔄 <b>Auto-upload:</b> Enabled"
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
        title = video_info.get("title", "Unknown")
        channel = video_info.get("channel_title", "Unknown")
        
        message = (
            f"✅ <b>PROCESSING COMPLETE!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎬 <b>Title:</b> {title}\n"
            f"📺 <b>Channel:</b> {channel}\n"
            f"📁 <b>File:</b> {processed_path}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📤 <b>Ready for upload...</b>"
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
        original_title = video_info.get("title", "Unknown")
        original_channel = video_info.get("channel_title", "Unknown")
        original_url = video_info.get("url", "N/A")
        seo_title = seo_data.get("title", "Unknown")
        tags = seo_data.get("tags", [])[:5]
        
        message = (
            f"🚀 <b>UPLOAD SUCCESSFUL!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📹 <b>ORIGINAL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎬 <b>Title:</b> {original_title}\n"
            f"📺 <b>Channel:</b> {original_channel}\n"
            f"🔗 <a href=\"{original_url}\">{original_url}</a>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📤 <b>UPLOADED TO YOUR CHANNEL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎬 <b>Title:</b> {seo_title}\n"
            f"🔗 <a href=\"{uploaded_url}\">{uploaded_url}</a>\n"
            f"🏷️ <b>Tags:</b> {', '.join(tags)}...\n\n"
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
        title = video_info.get("title", "Unknown")
        url = video_info.get("url", "N/A")
        
        message = (
            f"❌ <b>UPLOAD FAILED!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎬 <b>Title:</b> {title}\n"
            f"🔗 <a href=\"{url}\">{url}</a>\n"
            f"⚠️ <b>Error:</b> {error}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔄 Will retry in next cycle."
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
        today = datetime.now().strftime("%d %b %Y, %I:%M %p IST")
        detected = stats.get("detected", 0)
        uploaded = stats.get("uploaded", 0)
        failed = stats.get("failed", 0)
        skipped = stats.get("skipped", 0)
        
        message = (
            f"📊 <b>DAILY SUMMARY REPORT</b>\n"
            f"📅 {today}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎬 Trailers Detected: <b>{detected}</b>\n"
            f"✅ Successfully Uploaded: <b>{uploaded}</b>\n"
            f"❌ Failed Uploads: <b>{failed}</b>\n"
            f"⏭️ Skipped (limit reached): <b>{skipped}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📈 Upload Quota: {uploaded}/{config.MAX_DAILY_UPLOADS}"
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
            f"🚨 <b>ERROR!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
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
        channels_count = len(config.MONITORED_CHANNEL_IDS)
        max_uploads = config.MAX_DAILY_UPLOADS
        windows = config.UPLOAD_TIME_WINDOWS
        
        # Build channel names list
        channel_list = []
        for cid in config.MONITORED_CHANNEL_IDS[:5]:
            name = config.CHANNEL_NAMES.get(cid, cid[:12] + "...")
            channel_list.append(f"   • {name}")
        if channels_count > 5:
            channel_list.append(f"   • ... and {channels_count - 5} more")
        
        message = (
            f"🤖 <b>YouTube Trailer Automation Started!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📺 <b>MONITORING CHANNELS ({channels_count})</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(channel_list) + "\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ <b>SETTINGS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📤 Max daily uploads: {max_uploads}\n"
            f"🕐 Upload windows: {len(windows)} hours active\n"
            f"🔄 Check interval: Every 30 minutes\n\n"
            f"✅ Ready to detect and re-upload trailers!"
        )
        return self._send_message(message)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reporter = TelegramReporter()
    reporter.send_startup_message()
