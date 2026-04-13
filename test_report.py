"""
Test Script: Real Trailer Detection + Telegram Report
Detects actual new trailers from monitored channels and sends real report to Telegram.
Only tests detection and reporting - does NOT download, process, or upload anything.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from src.detector import TrailerDetector
from src.telegram_report import TelegramReporter

# Configure logging
log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler(config.LOG_DIR / "test_report.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def main():
    """Run real test - detect trailers and send actual Telegram report."""
    
    print("\n" + "=" * 60)
    print("🧪 REAL TRAILER DETECTION + TELEGRAM REPORT TEST")
    print("=" * 60 + "\n")
    
    # Step 1: Initialize detector
    print("📡 Initializing YouTube detector...")
    detector = TrailerDetector()
    
    if not detector.youtube:
        print("❌ YouTube API client not available! Check YOUTUBE_API_KEY in .env")
        return
    
    print("✅ YouTube API client ready\n")
    
    # Step 2: Detect new trailers (real data)
    print("🔍 Scanning monitored channels for new trailers...")
    print(f"   Monitoring {len(config.MONITORED_CHANNEL_IDS)} channels\n")
    
    # Load state to skip already processed
    state = config.load_state()
    processed_ids = set(state.get("processed_videos", {}).keys())
    
    trailers = detector.detect_new_trailers(
        hours=48,  # Look back 48 hours
        processed_ids=processed_ids,
    )
    
    print(f"\n🎬 Found {len(trailers)} new trailer(s)\n")
    
    if not trailers:
        print("No new trailers found. Sending 'no trailers' test message...")
        reporter = TelegramReporter()
        reporter.send_error(
            "Test Run: No new trailers found in last 48 hours",
            "Detection test completed successfully - just no new trailers"
        )
        print("✅ Test message sent to Telegram!")
        return
    
    # Step 3: For each trailer, find re-uploaders and send REAL report
    reporter = TelegramReporter()
    
    for i, trailer in enumerate(trailers[:3], 1):  # Max 3 for test
        print(f"\n{'─' * 50}")
        print(f" Trailer {i}/{min(len(trailers), 3)}: {trailer['title']}")
        print(f" Channel: {trailer['channel_title']}")
        print(f" URL: {trailer['url']}")
        print(f" Published: {trailer['published_at']}")
        
        # Find re-uploaders (real YouTube search)
        print(f"\n🔍 Searching for re-uploaders...")
        reuploaders = detector.find_reuploaders(trailer, max_results=5)
        print(f"   Found {len(reuploaders)} re-uploader(s)")
        
        for r in reuploaders:
            print(f"   • {r['channel_title']} - {r['url']}")
        
        # Send REAL report to Telegram
        print(f"\n📤 Sending report to Telegram (chat_id: {config.TELEGRAM_CHAT_ID})...")
        success = reporter.send_trailer_detected(trailer, reuploaders=reuploaders)
        
        if success:
            print(f"✅ Report sent successfully!")
        else:
            print(f"❌ Failed to send report!")
    
    print(f"\n{'=' * 60}")
    print(f"🧪 TEST COMPLETE!")
    print(f"   Trailers detected: {len(trailers)}")
    print(f"   Reports sent: {min(len(trailers), 3)}")
    print(f"   Check your Telegram for real reports!")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
