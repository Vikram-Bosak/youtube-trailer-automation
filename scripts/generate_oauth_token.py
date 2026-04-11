"""
OAuth Token Generation Script
Run this script once to generate the OAuth refresh token.
This only needs to be done once - the token will be saved for future use.

Usage:
    python scripts/generate_oauth_token.py

The script will:
1. Open a browser window for Google OAuth consent
2. Generate an access token and refresh token
3. Save the token to oauth_token.json
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow
import config


def generate_token():
    """Generate OAuth token for YouTube and Google Drive access."""
    
    secrets_path = Path(config.GOOGLE_CLIENT_SECRETS_FILE)
    
    if not secrets_path.exists():
        print(f"❌ Client secrets file not found: {secrets_path}")
        print(f"   Please download it from Google Cloud Console and save as: {secrets_path}")
        sys.exit(1)

    # Combine all required scopes
    all_scopes = config.YOUTUBE_SCOPES + config.DRIVE_SCOPES + config.YOUTUBE_READONLY_SCOPES

    print("=" * 60)
    print("YouTube Trailer Automation - OAuth Token Generator")
    print("=" * 60)
    print()
    print(f"📋 Client Secrets: {secrets_path}")
    print(f"🔑 Required Scopes:")
    for scope in all_scopes:
        print(f"   - {scope}")
    print()
    print("🌐 A browser window will open for Google OAuth consent.")
    print("   Please sign in with the Google account associated with your YouTube channel.")
    print()

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(secrets_path),
            scopes=all_scopes,
        )

        # Run the OAuth flow
        creds = flow.run_local_server(
            port=8080,
            success_message="✅ Authentication successful! You can close this window.",
            open_browser=True,
        )

        # Save the token
        token_path = Path(config.GOOGLE_OAUTH_TOKEN_FILE)
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes),
        }

        with open(token_path, "w") as f:
            json.dump(token_data, f, indent=2)

        print()
        print("=" * 60)
        print("✅ OAuth Token Generated Successfully!")
        print("=" * 60)
        print()
        print(f"📁 Token saved to: {token_path}")
        print(f"🔄 Refresh Token: {creds.refresh_token[:20]}...")
        print()
        print("🎉 You can now run the trailer automation!")

    except FileNotFoundError:
        print(f"❌ Client secrets file not found: {secrets_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error generating token: {e}")
        sys.exit(1)


if __name__ == "__main__":
    generate_token()
