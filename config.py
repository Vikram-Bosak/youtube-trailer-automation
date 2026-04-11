"""
Configuration module for YouTube Trailer Automation.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# --- Project Paths ---
BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "./downloads"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", "./processed"))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "./backups"))
LOG_DIR = Path(os.getenv("LOG_DIR", "./logs"))
STATE_FILE = Path(os.getenv("STATE_FILE", "./data/state.json"))

# Ensure directories exist
for d in [DOWNLOAD_DIR, PROCESSED_DIR, BACKUP_DIR, LOG_DIR, STATE_FILE.parent]:
    d.mkdir(parents=True, exist_ok=True)

# --- Google Cloud / YouTube ---
GOOGLE_CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE", "client_secrets.json")
GOOGLE_OAUTH_TOKEN_FILE = os.getenv("GOOGLE_OAUTH_TOKEN_FILE", "oauth_token.json")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
MONITORED_CHANNEL_IDS = [
    cid.strip()
    for cid in os.getenv("MONITORED_CHANNEL_IDS", "").split(",")
    if cid.strip()
]

# --- Google Drive ---
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

# --- Gemini AI ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Upload Settings ---
MAX_DAILY_UPLOADS = int(os.getenv("MAX_DAILY_UPLOADS", "5"))
UPLOAD_TIME_WINDOWS = [
    int(w.strip())
    for w in os.getenv("UPLOAD_TIME_WINDOWS", "9,12,15,18,21").split(",")
    if w.strip()
]

# --- FFmpeg Settings ---
FFMPEG_MIRROR = os.getenv("FFMPEG_MIRROR", "true").lower() == "true"
FFMPEG_SPEED = float(os.getenv("FFMPEG_SPEED", "1.05"))
FFMPEG_CROP_PERCENT = int(os.getenv("FFMPEG_CROP_PERCENT", "3"))
FFMPEG_BRIGHTNESS = float(os.getenv("FFMPEG_BRIGHTNESS", "0.02"))
FFMPEG_CONTRAST = float(os.getenv("FFMPEG_CONTRAST", "1.02"))
FFMPEG_SATURATION = float(os.getenv("FFMPEG_SATURATION", "1.03"))

# --- YouTube API Scopes ---
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_READONLY_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# --- State Management ---
def load_state() -> dict:
    """Load state from state.json file."""
    import json
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {
        "processed_videos": {},
        "daily_upload_count": 0,
        "last_upload_date": None,
    }

def save_state(state: dict):
    """Save state to state.json file."""
    import json
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
