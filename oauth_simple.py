"""OAuth - use run_local_server with open_browser=True (single flow, no PKCE mismatch)"""
import os, json, sys
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv
load_dotenv()

secrets_file = os.getenv('GOOGLE_CLIENT_SECRETS_FILE', 'client_secrets.json')
all_scopes = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/drive.file',
]

flow = InstalledAppFlow.from_client_secrets_file(secrets_file, scopes=all_scopes)

# Let run_local_server handle EVERYTHING - it will open browser and catch callback
# This ensures code_verifier matches since it's all one flow
print('Starting OAuth - browser will open automatically...')
creds = flow.run_local_server(
    port=8080,
    open_browser=True,
    timeout_seconds=600,
    success_message='SUCCESS! Token saved. Close this tab.',
    redirect_uri_trailing_slash=True,
)

token_path = os.getenv('GOOGLE_OAUTH_TOKEN_FILE', 'oauth_token.json')
token_data = {
    'token': creds.token,
    'refresh_token': creds.refresh_token,
    'token_uri': creds.token_uri,
    'client_id': creds.client_id,
    'client_secret': creds.client_secret,
    'scopes': list(creds.scopes),
}
with open(token_path, 'w') as f:
    json.dump(token_data, f, indent=2)

print('OAUTH_SUCCESS!')
print(f'Token saved to: {token_path}')
