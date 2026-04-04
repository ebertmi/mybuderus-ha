"""Tests for auth.py."""
import pytest
import aiohttp
from aioresponses import aioresponses

from custom_components.mybuderus.auth import (
    build_auth_url,
    exchange_code,
    extract_code,
    generate_pkce_pair,
    refresh_access_token,
)
from custom_components.mybuderus.const import (
    AUTHORIZATION_ENDPOINT,
    CLIENT_ID,
    REDIRECT_URI,
    TOKEN_ENDPOINT,
)


def test_generate_pkce_pair_returns_two_strings():
    verifier, challenge = generate_pkce_pair()
    assert isinstance(verifier, str) and len(verifier) > 40
    assert isinstance(challenge, str) and len(challenge) > 40
    assert verifier != challenge


def test_pkce_challenge_is_s256_of_verifier():
    import base64, hashlib
    verifier, challenge = generate_pkce_pair()
    digest = hashlib.sha256(verifier.encode()).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    assert challenge == expected


def test_build_auth_url_contains_required_params():
    url = build_auth_url("testchallenge")
    assert AUTHORIZATION_ENDPOINT in url
    assert f"client_id={CLIENT_ID}" in url
    assert "code_challenge=testchallenge" in url
    assert "code_challenge_method=S256" in url
    assert "response_type=code" in url


def test_extract_code_from_full_url():
    url = "com.buderus.tt.dashtt://app/login?code=ABC123&session_state=xyz"
    assert extract_code(url) == "ABC123"


def test_extract_code_from_plain_code():
    assert extract_code("  MYCODE123  ") == "MYCODE123"


def test_extract_code_raises_on_error_url():
    url = "com.buderus.tt.dashtt://app/login?error=access_denied"
    with pytest.raises(ValueError, match="Auth error"):
        extract_code(url)


def test_extract_code_raises_on_url_without_code():
    url = "com.buderus.tt.dashtt://app/login?session_state=xyz"
    with pytest.raises(ValueError, match="No code"):
        extract_code(url)


@pytest.mark.asyncio
async def test_exchange_code_returns_token_dict():
    with aioresponses() as mock:
        mock.post(
            TOKEN_ENDPOINT,
            payload={
                "access_token": "acc123",
                "refresh_token": "ref456",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )
        async with aiohttp.ClientSession() as session:
            result = await exchange_code(session, "code_abc", "verifier_xyz")

    assert result["access_token"] == "acc123"
    assert result["refresh_token"] == "ref456"
    assert result["expires_in"] == 3600


@pytest.mark.asyncio
async def test_exchange_code_raises_on_http_error():
    with aioresponses() as mock:
        mock.post(TOKEN_ENDPOINT, status=400, payload={"error": "invalid_grant"})
        async with aiohttp.ClientSession() as session:
            with pytest.raises(aiohttp.ClientResponseError):
                await exchange_code(session, "bad_code", "verifier")


@pytest.mark.asyncio
async def test_refresh_access_token_returns_new_token():
    with aioresponses() as mock:
        mock.post(
            TOKEN_ENDPOINT,
            payload={
                "access_token": "new_acc",
                "refresh_token": "new_ref",
                "expires_in": 3600,
            },
        )
        async with aiohttp.ClientSession() as session:
            result = await refresh_access_token(session, "old_refresh")

    assert result["access_token"] == "new_acc"


@pytest.mark.asyncio
async def test_refresh_access_token_raises_on_401():
    with aioresponses() as mock:
        mock.post(TOKEN_ENDPOINT, status=401, payload={"error": "invalid_token"})
        async with aiohttp.ClientSession() as session:
            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await refresh_access_token(session, "expired_refresh")
    assert exc_info.value.status == 401
