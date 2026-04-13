"""OAuth helper - starts local server and waits for callback."""
import json, sys, webbrowser
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from google_auth_oauthlib.flow import InstalledAppFlow
import config

secrets_path = Path(config.GOOGLE_CLIENT_SECRETS_FILE)
all_scopes = config.YOUTUBE_SCOPES + config.DRIVE_SCOPES + config.YOUTUBE_READONLY_SCOPES

print("Starting OAuth flow on port 8080...")

flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), scopes=all_scopes)

# Generate auth URL and open browser manually
auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

print(f"Opening browser...")
webbrowser.open(auth_url)

# Now run the local server to catch the callback
creds = flow.run_local_server(
    port=8080,
    open_browser=False,  # Already opened above
    timeout_seconds=300,
    success_message="Authentication successful! You can close this tab.",
)

# Save token
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

print(f"Token saved to: {token_path}")
print("OAUTH_SUCCESS")
