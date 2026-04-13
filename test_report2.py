"""
Test Script 2: Force detect a real trailer from popular channels
Searches for actual recent trailers on YouTube and sends real Telegram report.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from src.detector import TrailerDetector
from src.telegram_report import TelegramReporter

log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler(config.LOG_DIR / "test_report2.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def main():
    print("\n" + "=" * 60)
    print("🧪 FORCE TRAILER DETECTION + REAL TELEGRAM REPORT")
    print("=" * 60 + "\n")
    
    detector = TrailerDetector()
    reporter = TelegramReporter()
    
    if not detector.youtube:
        print("❌ YouTube API not available!")
        return
    
    # Search for recent trailers using YouTube search (not just monitored channels)
    print("🔍 Searching YouTube for latest movie trailers...\n")
    
    from googleapiclient.errors import HttpError
    from datetime import datetime, timedelta
    
    search_queries = [
        "official trailer 2025",
        "official trailer 2026",
    ]
    
    found_trailers = []
    
    for query in search_queries:
        try:
            request = detector.youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=5,
                order="date",
                publishedAfter=(
                    datetime.utcnow() - timedelta(days=7)
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            response = request.execute()
            
            for item in response.get("items", []):
                vid_id = item["id"].get("videoId", "")
                if not vid_id:
                    continue
                    
                # Check if it looks like a trailer
                title = item["snippet"]["title"].lower()
                if any(kw in title for kw in ["trailer", "teaser"]) and \
                   not any(kw in title for kw in ["reaction", "review", "breakdown", "fan made"]):
                    
                    trailer_info = {
                        "video_id": vid_id,
                        "title": item["snippet"]["title"],
                        "channel_title": item["snippet"]["channelTitle"],
                        "published_at": item["snippet"]["publishedAt"],
                        "description": item["snippet"].get("description", "")[:200],
                        "thumbnail": item["snippet"]["thumbnails"].get("high", {}).get("url", ""),
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                    }
                    
                    # Avoid duplicates
                    if not any(t["video_id"] == vid_id for t in found_trailers):
                        found_trailers.append(trailer_info)
                        
        except HttpError as e:
            print(f"❌ Search error: {e}")
    
    print(f"🎬 Found {len(found_trailers)} real trailer(s) on YouTube\n")
    
    if not found_trailers:
        print("No trailers found! Sending test message anyway...")
        reporter.send_error(
            "Test: No trailers found via search either",
            "Search test"
        )
        return
    
    # Take the first real trailer and send full report
    trailer = found_trailers[0]
    
    print(f"📹 Using trailer: {trailer['title']}")
    print(f"📺 Channel: {trailer['channel_title']}")
    print(f"🔗 URL: {trailer['url']}")
    print(f"📅 Published: {trailer['published_at']}")
    
    # Find re-uploaders for this trailer
    print(f"\n🔍 Finding re-uploaders...")
    reuploaders = detector.find_reuploaders(trailer, max_results=5)
    print(f"   Found {len(reuploaders)} re-uploader(s)")
    
    for r in reuploaders:
        print(f"   • {r['channel_title']}")
    
    # Send REAL report to Telegram
    print(f"\n📤 Sending REAL report to Telegram...")
    success = reporter.send_trailer_detected(trailer, reuploaders=reuploaders)
    
    if success:
        print(f"✅ REAL report sent to Telegram! Check your chat!")
    else:
        print(f"❌ Failed to send report")
    
    print(f"\n{'=' * 60}")
    print(f"🧪 TEST COMPLETE - Check Telegram for real data!")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
