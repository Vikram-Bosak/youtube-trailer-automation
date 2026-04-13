"""
Main Orchestrator Module
Coordinates all pipeline steps:
1. Detect new trailers
2. Download
3. Process (copyright protection)
4. Generate SEO content
5. Upload to YouTube
6. Backup to Google Drive
7. Send Telegram reports
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from src.detector import TrailerDetector
from src.downloader import VideoDownloader
from src.processor import VideoProcessor
from src.seo_generator import SEOGenerator
from src.uploader import YouTubeUploader
from src.drive_backup import DriveBackup
from src.telegram_report import TelegramReporter

# Configure logging
log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler(config.LOG_DIR / "automation.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class TrailerAutomation:
    """Main orchestrator for the YouTube Trailer Automation pipeline."""

    def __init__(self):
        logger.info("Initializing YouTube Trailer Automation...")

        # Initialize all modules
        self.detector = TrailerDetector()
        self.downloader = VideoDownloader()
        self.processor = VideoProcessor()
        self.seo_generator = SEOGenerator()
        self.uploader = YouTubeUploader()
        self.drive_backup = DriveBackup()
        self.reporter = TelegramReporter()

        # Load state
        self.state = config.load_state()

        # Stats for reporting
        self.stats = {
            "detected": 0,
            "uploaded": 0,
            "failed": 0,
            "skipped": 0,
        }

        logger.info("All modules initialized")

    def process_trailer(self, video_info: dict) -> bool:
        """
        Process a single trailer through the complete pipeline.
        
        Args:
            video_info: Video info dict from detector
            
        Returns:
            True if successfully uploaded
        """
        video_id = video_info["video_id"]
        original_title = video_info.get("title", "Unknown")

        try:
            # Step 1: Find re-uploaders (other channels that uploaded same trailer)
            logger.info(f"[0/6] Finding re-uploaders for: {original_title}")
            reuploaders = self.detector.find_reuploaders(video_info, max_results=5)
            video_info["reuploaders"] = reuploaders
            logger.info(f"Found {len(reuploaders)} re-uploader(s)")

            # Step 1b: Notify detection with real data + re-uploaders
            self.reporter.send_trailer_detected(video_info, reuploaders=reuploaders)

            # Step 2: Download
            logger.info(f"[1/6] Downloading: {original_title}")
            download_path = self.downloader.download(
                video_info["url"], video_id
            )
            if not download_path:
                raise Exception("Download failed")

            # Step 3: Process (copyright protection)
            logger.info(f"[2/6] Processing: {original_title}")
            processed_path = self.processor.process(download_path, video_id)
            if not processed_path:
                raise Exception("Processing failed")

            self.reporter.send_processing_complete(
                video_info, str(processed_path)
            )

            # Step 4: Generate SEO content
            logger.info(f"[3/6] Generating SEO: {original_title}")
            seo_data = self.seo_generator.generate_seo_content(
                original_title=original_title,
                original_description=video_info.get("description", ""),
                channel_name=video_info.get("channel_title", ""),
                video_url=video_info.get("url", ""),
            )

            # Step 5: Upload to YouTube
            logger.info(f"[4/6] Uploading: {seo_data['title']}")
            uploaded_id = self.uploader.upload_with_schedule(
                video_path=processed_path,
                title=seo_data["title"],
                description=seo_data["description"],
                tags=seo_data["tags"],
                state=self.state,
                video_id=video_id,
            )

            if not uploaded_id:
                # Upload failed or skipped (limit/window)
                self.stats["skipped"] += 1
                logger.warning(f"Upload skipped/failed for: {original_title}")

                # Clean up downloaded file but keep processed for retry
                self.downloader.cleanup(video_id)
                return False

            uploaded_url = f"https://www.youtube.com/watch?v={uploaded_id}"

            # Step 6: Backup to Google Drive
            logger.info(f"[5/6] Backing up: {original_title}")
            self.drive_backup.upload_file(
                processed_path,
                description=f"Re-uploaded trailer: {seo_data['title']}"
            )

            # Backup metadata
            metadata = {
                "original_video_id": video_id,
                "original_url": video_info.get("url", ""),
                "original_title": original_title,
                "original_channel": video_info.get("channel_title", ""),
                "uploaded_video_id": uploaded_id,
                "uploaded_url": uploaded_url,
                "seo_data": seo_data,
                "processed_at": datetime.now().isoformat(),
            }
            self.drive_backup.upload_metadata(video_id, metadata)

            # Step 7: Report success
            logger.info(f"[6/6] Reporting success: {original_title}")
            self.reporter.send_upload_success(video_info, uploaded_url, seo_data)

            # Update state
            self.state["processed_videos"][video_id] = {
                "original_title": original_title,
                "uploaded_id": uploaded_id,
                "uploaded_url": uploaded_url,
                "processed_at": datetime.now().isoformat(),
            }
            config.save_state(self.state)

            # Cleanup
            self.downloader.cleanup(video_id)
            self.processor.cleanup(video_id)

            self.stats["uploaded"] += 1
            logger.info(f"✅ Successfully processed: {original_title}")
            return True

        except Exception as e:
            logger.error(f"❌ Error processing {original_title}: {e}")
            self.reporter.send_upload_failed(video_info, str(e))
            self.stats["failed"] += 1

            # Cleanup on failure
            self.downloader.cleanup(video_id)
            self.processor.cleanup(video_id)

            return False

    def run_once(self) -> dict:
        """
        Run one detection cycle.
        
        Returns:
            Stats dict for this cycle
        """
        logger.info("=" * 50)
        logger.info("Starting detection cycle...")
        logger.info("=" * 50)

        # Get already processed video IDs
        processed_ids = set(self.state.get("processed_videos", {}).keys())

        # Detect new trailers
        new_trailers = self.detector.detect_new_trailers(
            hours=48,
            processed_ids=processed_ids,
        )

        self.stats["detected"] += len(new_trailers)

        if not new_trailers:
            logger.info("No new trailers found in this cycle")
            return self.stats

        logger.info(f"Found {len(new_trailers)} new trailer(s) to process")

        # Process each trailer
        for i, trailer in enumerate(new_trailers, 1):
            logger.info(f"Processing trailer {i}/{len(new_trailers)}")
            
            # Check daily limit before each upload
            if not self.uploader.can_upload_today(self.state):
                logger.warning("Daily upload limit reached, stopping")
                self.stats["skipped"] += len(new_trailers) - i + 1
                break

            self.process_trailer(trailer)

        logger.info("Detection cycle complete")
        return self.stats

    def run(self, interval_minutes: int = 30):
        """
        Run the automation continuously.
        
        Args:
            interval_minutes: Check interval in minutes
        """
        self.reporter.send_startup_message()

        logger.info(
            f"Starting automation with {interval_minutes} minute intervals"
        )

        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error in automation cycle: {e}")
                self.reporter.send_error(
                    f"Automation cycle error: {e}", "run_once"
                )

            # Wait for next cycle
            logger.info(
                f"Next check in {interval_minutes} minutes "
                f"(at {datetime.now().strftime('%H:%M:%S')})"
            )
            time.sleep(interval_minutes * 60)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="YouTube Trailer Automation"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run only one detection cycle",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Check interval in minutes (default: 30)",
    )

    args = parser.parse_args()

    automation = TrailerAutomation()

    if args.once:
        stats = automation.run_once()
        automation.reporter.send_daily_summary(stats)
    else:
        automation.run(interval_minutes=args.interval)


if __name__ == "__main__":
    main()
