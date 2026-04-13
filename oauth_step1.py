"""
Simple OAuth: Step 1 - Get the auth URL manually
Step 2 - User visits URL in browser and copies the callback URL
Step 3 - Exchange code for token
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from google_auth_oauthlib.flow import InstalledAppFlow
import config

secrets_path = Path(config.GOOGLE_CLIENT_SECRETS_FILE)
all_scopes = config.YOUTUBE_SCOPES + config.DRIVE_SCOPES + config.YOUTUBE_READONLY_SCOPES

flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), scopes=all_scopes)

# Step 1: Generate auth URL
auth_url, state = flow.authorization_url(prompt='consent', access_type='offline')

# Save flow state for step 2
flow_data = {
    'client_id': flow.client_config['client_id'],
    'client_secret': flow.client_config['client_secret'],
    'state': state,
    'code_verifier': flow.code_verifier,
}
with open('oauth_flow_state.json', 'w') as f:
    json.dump(flow_data, f, indent=2)

print("=" * 70)
print("STEP 1: Open this URL in your browser and login with Google:")
print("=" * 70)
print()
print(auth_url)
print()
print("=" * 70)
print("After login, browser will redirect to localhost:8080")
print("The page will show an error - THAT'S OK!")
print("Copy the FULL URL from the browser address bar")
print("It will look like: http://localhost:8080/?state=...&code=...")
print("=" * 70)
