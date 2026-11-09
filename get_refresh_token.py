"""
Run this script locally ONCE on your PC to authorize your YouTube account
and obtain the YT_REFRESH_TOKEN for GitHub Actions secrets.

Prerequisites:
    pip install google-auth-oauthlib google-api-python-client

Usage:
    python get_refresh_token.py
"""

import json
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

def main():
    print("=" * 60)
    print("YouTube OAuth Refresh Token Generator")
    print("=" * 60)

    client_id = input("Enter your Google Client ID: ").strip()
    client_secret = input("Enter your Google Client Secret: ").strip()

    if not client_id or not client_secret:
        print("Error: Both Client ID and Client Secret are required.")
        return

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost", "http://127.0.0.1"]
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    print("\n" + "=" * 60)
    print("SUCCESS! Add these to your GitHub Repository Secrets:")
    print("=" * 60)
    print(f"YT_CLIENT_ID:     {client_id}")
    print(f"YT_CLIENT_SECRET: {client_secret}")
    print(f"YT_REFRESH_TOKEN:  {creds.refresh_token}")
    print("=" * 60)

if __name__ == "__main__":
    main()
