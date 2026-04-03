"""
OAuth2 PKCE Auth für SingleKey ID.

Flow:
1. PKCE code_verifier + code_challenge generieren
2. Authorization URL bauen und Browser öffnen
3. User kopiert die Redirect-URL aus dem Browser (Custom-Scheme schlägt fehl)
4. Code aus der URL extrahieren
5. Code gegen Access + Refresh Token tauschen
6. Token cachen (token_cache.json)
"""
import base64
import hashlib
import json
import secrets
import time
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

CLIENT_ID = "762162C0-FA2D-4540-AE66-6489F189FADC"
AUTHORIZATION_ENDPOINT = "https://singlekey-id.com/auth/connect/authorize"
TOKEN_ENDPOINT = "https://singlekey-id.com/auth/connect/token"
REDIRECT_URI = "com.buderus.tt.dashtt://app/login"
SCOPES = " ".join([
    "openid",
    "email",
    "profile",
    "offline_access",
    "pointt.gateway.list",
    "pointt.gateway.resource.dashapp",
    "pointt.castt.flow.token-exchange",
    "bacon",
    "hcc.tariff.read",
])
TOKEN_CACHE_FILE = Path(__file__).parent / "token_cache.json"


def _generate_pkce_pair() -> tuple[str, str]:
    """Returns (code_verifier, code_challenge) for PKCE S256."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def _exchange_code(code: str, code_verifier: str) -> dict:
    """Exchange authorization code for tokens."""
    resp = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _refresh(refresh_token: str) -> dict:
    """Refresh an expired access token."""
    resp = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": refresh_token,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _save(token_data: dict) -> None:
    token_data["cached_at"] = time.time()
    TOKEN_CACHE_FILE.write_text(json.dumps(token_data, indent=2))


def _load() -> dict | None:
    if not TOKEN_CACHE_FILE.exists():
        return None
    try:
        return json.loads(TOKEN_CACHE_FILE.read_text())
    except Exception:
        return None


def _expired(token_data: dict) -> bool:
    cached_at = token_data.get("cached_at", 0)
    expires_in = token_data.get("expires_in", 3600)
    return time.time() > cached_at + expires_in - 60


def get_access_token() -> str:
    """
    Returns a valid access token.
    Uses cache if available, refreshes if expired, otherwise starts browser login.
    """
    cached = _load()
    if cached:
        if not _expired(cached):
            print("✓ Nutze gecachten Access Token.")
            return cached["access_token"]
        if cached.get("refresh_token"):
            print("↻ Token abgelaufen, refreshe...")
            try:
                new_token = _refresh(cached["refresh_token"])
                _save(new_token)
                print("✓ Token erneuert.")
                return new_token["access_token"]
            except Exception as e:
                print(f"  Refresh fehlgeschlagen ({e}), starte neu...")

    # New login
    code_verifier, code_challenge = _generate_pkce_pair()
    auth_url = AUTHORIZATION_ENDPOINT + "?" + urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "login",
    })

    print("\n🔐 SingleKey ID Login")
    print("=" * 60)
    print("SCHRITTE:")
    print("1. Browser öffnet sich mit der SingleKey ID Login-Seite")
    print("2. Gib deine SingleKey ID Zugangsdaten ein und klicke 'Anmelden'")
    print("3. Nach erfolgreichem Login versucht der Browser zu dieser URL")
    print("   weiterzuleiten (die URL beginnt mit 'com.buderus...'):")
    print("     com.buderus.tt.dashtt://app/login?code=XXXX...")
    print("4. Der Browser kann diese URL NICHT öffnen und zeigt einen Fehler")
    print("   → In Chrome: 'ERR_UNKNOWN_URL_SCHEME' — die URL steht in der Adressleiste")
    print("   → In Safari: Dialog 'Safari kann die Seite nicht öffnen'")
    print("5. Kopiere die vollständige URL aus der Adressleiste")
    print("   (beginnt mit 'com.buderus.tt.dashtt://app/login?code=')")
    print("")
    print("WICHTIG: Kopiere NICHT die URL der Login-Seite (singlekey-id.com/...)")
    print("         Kopiere die URL NACH dem Login (com.buderus.tt.dashtt://...)")
    print("=" * 60)
    webbrowser.open(auth_url)

    redirect_url = input("\nRedirect-URL oder nur den Code einfügen: ").strip()

    # Akzeptiere entweder die vollständige URL oder nur den Code-String
    if redirect_url.startswith("com.buderus") or redirect_url.startswith("http"):
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)
        if "error" in params:
            raise RuntimeError(f"Auth-Fehler: {params['error'][0]}")
        if "code" not in params:
            raise ValueError(
                f"Kein 'code' in URL gefunden.\n"
                f"Eingabe war: {redirect_url}\n"
                f"Erwartetes Format: com.buderus.tt.dashtt://app/login?code=XXXX"
            )
        code = params["code"][0]
    else:
        # Benutzer hat nur den Code eingefügt
        code = redirect_url

    token_data = _exchange_code(code, code_verifier)
    _save(token_data)
    print("✓ Login erfolgreich, Token gecacht.")
    return token_data["access_token"]


if __name__ == "__main__":
    token = get_access_token()
    print(f"\nAccess Token (erste 40 Zeichen): {token[:40]}...")
