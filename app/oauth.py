"""Google + LinkedIn OAuth (Authlib). Optional – works when client IDs are set."""

from __future__ import annotations
from typing import Optional
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from app.core.config import get_settings

_oauth: Optional[OAuth] = None


def get_oauth() -> OAuth:
    global _oauth
    if _oauth is not None:
        return _oauth
    s = get_settings()
    config = Config(environ={
        "GOOGLE_CLIENT_ID": s.google_client_id or "",
        "GOOGLE_CLIENT_SECRET": s.google_client_secret or "",
        "LINKEDIN_CLIENT_ID": s.linkedin_client_id or "",
        "LINKEDIN_CLIENT_SECRET": s.linkedin_client_secret or "",
    })
    oauth = OAuth(config)
    if s.google_client_id and s.google_client_secret:
        oauth.register(
            name="google",
            client_id=s.google_client_id,
            client_secret=s.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    if s.linkedin_client_id and s.linkedin_client_secret:
        oauth.register(
            name="linkedin",
            client_id=s.linkedin_client_id,
            client_secret=s.linkedin_client_secret,
            access_token_url="https://www.linkedin.com/oauth/v2/accessToken",
            authorize_url="https://www.linkedin.com/oauth/v2/authorization",
            api_base_url="https://api.linkedin.com/v2/",
            client_kwargs={"scope": "openid profile email"},
        )
    _oauth = oauth
    return oauth


def oauth_enabled() -> dict:
    s = get_settings()
    return {
        "google": bool(s.google_client_id and s.google_client_secret),
        "linkedin": bool(s.linkedin_client_id and s.linkedin_client_secret),
    }
