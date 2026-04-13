"""
OAuth flow - starts server, prints URL, waits for callback.
Run this script, then open the printed URL in your browser.
"""
import os, json, sys
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from google_auth_oauthlib.flow import InstalledAppFlow
import config

secrets_path = Path(config.GOOGLE_CLIENT_SECRETS_FILE)
all_scopes = config.YOUTUBE_SCOPES + config.DRIVE_SCOPES + config.YOUTUBE_READONLY_SCOPES

flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), scopes=all_scopes)

# Step 1: Generate the auth URL
auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

print("AUTH_URL_START")
print(auth_url)
print("AUTH_URL_END")
print()
print("Waiting for callback on http://localhost:8080 ...")
print("Open the URL above in your browser, login and click Allow.")
print()

# Step 2: Start the local server and wait for the callback
creds = flow.run_local_server(
    port=8080,
    open_browser=False,
    timeout_seconds=600,
    success_message="SUCCESS! You can close this tab now.",
)

# Step 3: Save the token
token_path = Path(config.GOOGLE_OAUTH_TOKEN_FILE)
token_data = {
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri": creds.token_uri,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
    "scopes": list(creds.scopes),
}
with open(token_path, 'w') as f:
    json.dump(token_data, f, indent=2)

print()
print("=" * 60)
print("OAUTH SUCCESS! Token saved!")
print(f"File: {token_path}")
print("=" * 60)
