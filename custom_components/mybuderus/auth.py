"""OAuth2 PKCE authentication for SingleKey ID."""
import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp

from .const import (
    AUTHORIZATION_ENDPOINT,
    CLIENT_ID,
    REDIRECT_URI,
    SCOPES,
    TOKEN_ENDPOINT,
)


def generate_pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for PKCE S256."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def build_auth_url(code_challenge: str) -> str:
    """Build the SingleKey ID authorization URL for the user to open."""
    return AUTHORIZATION_ENDPOINT + "?" + urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "login",
    })


def extract_code(redirect_input: str) -> str:
    """Extract authorization code from full redirect URL or plain code string.

    Accepts:
    - Full URL: com.buderus.tt.dashtt://app/login?code=XXX&...
    - Plain code: XXX
    """
    redirect_input = redirect_input.strip()
    if redirect_input.startswith("com.buderus") or redirect_input.startswith("http"):
        parsed = urlparse(redirect_input)
        params = parse_qs(parsed.query)
        if "error" in params:
            raise ValueError(f"Auth error: {params['error'][0]}")
        if "code" not in params:
            raise ValueError("No code in URL")
        return params["code"][0]
    return redirect_input


async def exchange_code(
    session: aiohttp.ClientSession, code: str, code_verifier: str
) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    async with session.post(
        TOKEN_ENDPOINT,
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier,
        },
    ) as resp:
        resp.raise_for_status()
        return await resp.json()


async def refresh_access_token(
    session: aiohttp.ClientSession, refresh_token: str
) -> dict:
    """Refresh an expired access token using the refresh token."""
    async with session.post(
        TOKEN_ENDPOINT,
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": refresh_token,
        },
    ) as resp:
        resp.raise_for_status()
        return await resp.json()
