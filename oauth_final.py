"""One-shot OAuth - opens browser and waits for callback in same flow."""
import os, json, sys, subprocess
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from google_auth_oauthlib.flow import InstalledAppFlow
import config

secrets_path = Path(config.GOOGLE_CLIENT_SECRETS_FILE)
all_scopes = config.YOUTUBE_SCOPES + config.DRIVE_SCOPES + config.YOUTUBE_READONLY_SCOPES

print("Creating OAuth flow...")
flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), scopes=all_scopes)

# Step 1: Generate auth URL (this also creates the code_verifier internally)
auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
print(f"Auth URL generated")

# Step 2: Open browser using Windows start command
subprocess.Popen(['cmd', '/c', 'start', '', auth_url], shell=True)
print("Browser opened! Please login and click Allow.")

# Step 3: Start local server on SAME flow object - code_verifier will match
print("Waiting for callback on http://localhost:8080 ...")
creds = flow.run_local_server(
    port=8080,
    open_browser=False,
    timeout_seconds=600,
    success_message="SUCCESS! You can close this tab now.",
)

# Step 4: Save token
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
