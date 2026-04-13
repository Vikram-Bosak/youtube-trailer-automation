"""
Test Script 3: Find a popular trailer with re-uploaders
Uses a well-known movie trailer that's been out for a few days
so we can find actual re-uploaders.
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
        logging.FileHandler(config.LOG_DIR / "test_report3.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def main():
    print("\n" + "=" * 60)
    print("🧪 POPULAR TRAILER + RE-UPLOADERS + REAL TELEGRAM REPORT")
    print("=" * 60 + "\n")
    
    detector = TrailerDetector()
    reporter = TelegramReporter()
    
    if not detector.youtube:
        print("❌ YouTube API not available!")
        return
    
    # Search for a popular recent trailer that will have re-uploaders
    print("🔍 Searching for popular recent trailers with re-uploaders...\n")
    
    from googleapiclient.errors import HttpError
    from datetime import datetime, timedelta
    
    # Search for popular trailers (longer time range = more re-uploaders)
    search_queries = [
        "Marvel Thunderbolts official trailer",
        "Mission Impossible official trailer",
        "Fast X official trailer",
        "Jurassic World official trailer",
    ]
    
    best_trailer = None
    best_reuploaders = []
    
    for query in search_queries:
        try:
            request = detector.youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=3,
                order="relevance",
                publishedAfter=(
                    datetime.utcnow() - timedelta(days=30)
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            response = request.execute()
            
            for item in response.get("items", []):
                vid_id = item["id"].get("videoId", "")
                if not vid_id:
                    continue
                    
                title = item["snippet"]["title"].lower()
                # Must be a trailer, not reaction/review
                if any(kw in title for kw in ["trailer", "teaser"]) and \
                   not any(kw in title for kw in ["reaction", "review", "breakdown"]):
                    
                    trailer_info = {
                        "video_id": vid_id,
                        "title": item["snippet"]["title"],
                        "channel_title": item["snippet"]["channelTitle"],
                        "published_at": item["snippet"]["publishedAt"],
                        "description": item["snippet"].get("description", "")[:200],
                        "thumbnail": item["snippet"]["thumbnails"].get("high", {}).get("url", ""),
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                    }
                    
                    # Find re-uploaders for this one
                    reuploaders = detector.find_reuploaders(trailer_info, max_results=5)
                    
                    print(f"  📹 {trailer_info['title']}")
                    print(f"     Channel: {trailer_info['channel_title']}")
                    print(f"     Re-uploaders found: {len(reuploaders)}")
                    
                    if len(reuploaders) > len(best_reuploaders):
                        best_trailer = trailer_info
                        best_reuploaders = reuploaders
                    
        except HttpError as e:
            print(f"❌ Search error: {e}")
    
    if not best_trailer:
        print("❌ No trailers found!")
        return
    
    print(f"\n{'─' * 50}")
    print(f"🎬 BEST MATCH: {best_trailer['title']}")
    print(f"📺 Channel: {best_trailer['channel_title']}")
    print(f"🔗 URL: {best_trailer['url']}")
    print(f"👥 Re-uploaders: {len(best_reuploaders)}")
    
    for i, r in enumerate(best_reuploaders, 1):
        print(f"   {i}. {r['channel_title']} - {r['url']}")
    
    # Send REAL report to Telegram with REAL data
    print(f"\n📤 Sending REAL report to Telegram (with re-uploaders)...")
    success = reporter.send_trailer_detected(best_trailer, reuploaders=best_reuploaders)
    
    if success:
        print(f"✅ REAL report sent! Check your Telegram NOW!")
    else:
        print(f"❌ Failed to send report")
    
    print(f"\n{'=' * 60}")
    print(f"🧪 TEST COMPLETE - Check Telegram for the new format!")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
