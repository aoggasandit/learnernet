#!/usr/bin/env python3
"""
Helper script to obtain a Gmail OAuth2 refresh token.

Usage:
1. Update CLIENT_ID and CLIENT_SECRET with your Google OAuth credentials from
   https://console.cloud.google.com/apis/credentials
2. Run this script: python get_refresh_token.py
3. A browser will open for you to authorize. Sign in and grant permission.
4. The script will print your refresh token. Copy it to .env
5. Delete this script after use.
"""

import os
import sys

# Fill these in from Google Cloud Console credentials
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
GMAIL_USER = "your_email@gmail.com"  # The Gmail account that will send emails

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main():
    if CLIENT_ID == "YOUR_CLIENT_ID" or CLIENT_SECRET == "YOUR_CLIENT_SECRET":
        print("ERROR: Please update CLIENT_ID and CLIENT_SECRET in this script.")
        print("Get them from: https://console.cloud.google.com/apis/credentials")
        sys.exit(1)

    try:
        from google.auth.oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: google-auth-oauthlib not installed.")
        print("Install: pip install google-auth google-auth-oauthlib google-api-python-client")
        sys.exit(1)

    # Create the OAuth2 flow
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        SCOPES,
    )

    print("Starting OAuth2 flow...")
    print("A browser will open. Sign in and grant permission to send emails.\n")

    # This will open a browser for you to authorize
    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 80)
    print("SUCCESS! Copy these values to your .env file:")
    print("=" * 80)
    print(f"\nGOOGLE_CLIENT_ID={CLIENT_ID}")
    print(f"GOOGLE_CLIENT_SECRET={CLIENT_SECRET}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print(f"GOOGLE_OAUTH_USER={GMAIL_USER}")

    print("\n" + "=" * 80)
    print("After saving to .env, restart the app and password resets will use Gmail OAuth.")
    print("=" * 80)


if __name__ == "__main__":
    main()
