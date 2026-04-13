"""
Simple OAuth: Step 2 - Take the callback URL and exchange for token
"""
import json, sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, str(Path(__file__).parent))
from google_auth_oauthlib.flow import InstalledAppFlow
import config

# Load flow state
with open('oauth_flow_state.json', 'r') as f:
    flow_data = json.load(f)

secrets_path = Path(config.GOOGLE_CLIENT_SECRETS_FILE)
all_scopes = config.YOUTUBE_SCOPES + config.DRIVE_SCOPES + config.YOUTUBE_READONLY_SCOPES

flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), scopes=all_scopes)

# Ask user for callback URL
print("Paste the FULL callback URL from browser (the one that failed to load):")
callback_url = input().strip()

# Extract the authorization code
parsed = urlparse(callback_url)
params = parse_qs(parsed.query)

if 'code' not in params:
    print("ERROR: No 'code' parameter found in URL!")
    print("Make sure you copied the full URL from the browser address bar")
    sys.exit(1)

code = params['code'][0]
state = params.get('state', [''])[0]

print(f"Got authorization code: {code[:20]}...")

# Exchange code for token
flow.fetch_token(code=code)

creds = flow.credentials

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
with open(token_path, 'w') as f:
    json.dump(token_data, f, indent=2)

print()
print("=" * 70)
print("OAUTH TOKEN SAVED SUCCESSFULLY!")
print(f"Token file: {token_path}")
print("You can now run the trailer automation!")
print("=" * 70)
