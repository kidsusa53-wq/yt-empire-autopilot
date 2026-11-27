"""Google OAuth 2.0 helpers for YouTube Data API v3 + Analytics.

No credentials are hardcoded. Client ID/secret come from env
(YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET) or a user-supplied
client_secret.json. Tokens live in token.json (gitignored).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
# Dashboard URL (GitHub Pages, static UI only — NO Vercel).
# NOTE: a static Pages site has no backend, so it cannot receive an OAuth
# callback at /api/auth/callback. For a real OAuth run use LOCAL_REDIRECT_URI
# (http://localhost:8080/) — see README "Google OAuth". PAGES_URL is the
# dashboard UI address only, not a working OAuth redirect.
PAGES_URL = "https://kulbeer683-sketch.github.io/yt-empire-autopilot/"
REDIRECT_URI = PAGES_URL
LOCAL_REDIRECT_URI = "http://localhost:8080/"
ROOT = Path(__file__).resolve().parent
TOKEN_FILE = ROOT / "token.json"


def get_oauth_flow(redirect_uri: str = REDIRECT_URI):
    """Build an InstalledApp / web OAuth flow from env or client_secret.json."""
    from google_auth_oauthlib.flow import Flow
    client_secret = ROOT / "client_secret.json"
    if client_secret.exists():
        return Flow.from_client_secrets_file(str(client_secret), scopes=SCOPES,
                                             redirect_uri=redirect_uri)
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret_val = os.environ.get("YOUTUBE_CLIENT_SECRET")
    if not client_id or not client_secret_val:
        raise RuntimeError(
            "Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET (see .env.example) "
            "or provide client_secret.json from Google Cloud Console.")
    return Flow.from_client_config(
        {"web": {"client_id": client_id, "client_secret": client_secret_val,
                 "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                 "token_uri": "https://oauth2.googleapis.com/token",
                 "redirect_uris": [REDIRECT_URI, LOCAL_REDIRECT_URI]}},
        scopes=SCOPES, redirect_uri=redirect_uri)


def get_authenticated_service():
    """Return an authenticated youtube (Data API v3) service."""
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        refresh = os.environ.get("YOUTUBE_REFRESH_TOKEN")
        if refresh:
            creds = Credentials(None, refresh_token=refresh,
                                token_uri="https://oauth2.googleapis.com/token",
                                client_id=os.environ.get("YOUTUBE_CLIENT_ID"),
                                client_secret=os.environ.get("YOUTUBE_CLIENT_SECRET"),
                                scopes=SCOPES)
            creds.refresh(Request())
        else:
            flow = get_oauth_flow(LOCAL_REDIRECT_URI)
            creds = flow.run_local_server(port=8080)
            TOKEN_FILE.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def get_analytics_service():
    """Return an authenticated youtubeAnalytics service (same credentials)."""
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    if not TOKEN_FILE.exists() and not os.environ.get("YOUTUBE_REFRESH_TOKEN"):
        raise RuntimeError("Authenticate first via get_authenticated_service().")
    # Reuse the same token file / refresh token as the Data API service.
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
    else:
        creds = Credentials(None, refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
                            token_uri="https://oauth2.googleapis.com/token",
                            client_id=os.environ.get("YOUTUBE_CLIENT_ID"),
                            client_secret=os.environ.get("YOUTUBE_CLIENT_SECRET"),
                            scopes=SCOPES)
        creds.refresh(Request())
    return build("youtubeAnalytics", "v2", credentials=creds)


def save_token_from_code(code: str, redirect_uri: str = REDIRECT_URI) -> dict:
    """Exchange an OAuth authorization code for tokens (used by the web callback)."""
    flow = get_oauth_flow(redirect_uri)
    flow.fetch_token(code=code)
    creds = flow.credentials
    TOKEN_FILE.write_text(creds.to_json())
    return json.loads(creds.to_json())
