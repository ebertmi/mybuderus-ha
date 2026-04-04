"""
Test ob der SingleKey ID OAuth-Server http://127.0.0.1 als Redirect-URI akzeptiert.

RFC 8252 Section 7.3 schreibt vor, dass Authorization Server die Loopback-IP
(127.0.0.1) mit beliebigem Port akzeptieren müssen.

Verwendung:
  python test_loopback_auth.py
"""
import base64
import hashlib
import secrets
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

CLIENT_ID = "762162C0-FA2D-4540-AE66-6489F189FADC"
AUTHORIZATION_ENDPOINT = "https://singlekey-id.com/auth/connect/authorize"
TOKEN_ENDPOINT = "https://singlekey-id.com/auth/connect/token"
SCOPES = "openid email profile offline_access pointt.gateway.list pointt.gateway.resource.dashapp pointt.castt.flow.token-exchange bacon hcc.tariff.read"


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _generate_pkce_pair() -> tuple[str, str]:
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def test_loopback_redirect():
    port = _find_free_port()
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    code_verifier, code_challenge = _generate_pkce_pair()

    received = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            if "error" in params:
                received["error"] = params["error"][0]
            elif "code" in params:
                received["code"] = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if "code" in received:
                self.wfile.write(b"<h1>Login erfolgreich!</h1><p>Du kannst diesen Tab schliessen.</p>")
            else:
                self.wfile.write(f"<h1>Fehler</h1><pre>{params}</pre>".encode())

        def log_message(self, format, *args):
            pass  # Suppress request logs

    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.daemon = True
    thread.start()

    auth_url = AUTHORIZATION_ENDPOINT + "?" + urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "login",
    })

    print(f"\nTest: Loopback-Redirect auf {redirect_uri}")
    print("Browser öffnet sich...")
    webbrowser.open(auth_url)
    print("Warte auf Redirect vom Browser (max. 120 Sekunden)...")

    thread.join(timeout=120)
    server.server_close()

    if "code" in received:
        print(f"\n✓ ERFOLG! Authorization Code empfangen: {received['code'][:20]}...")
        print("  → Loopback-Redirect funktioniert. Kann für HA-Integration verwendet werden.")
    elif "error" in received:
        print(f"\n✗ Auth-Fehler: {received['error']}")
        print("  → Server hat den Loopback-Redirect abgelehnt.")
    else:
        print("\n✗ Kein Callback empfangen (Timeout oder Browser-Fehler).")
        print("  → Wahrscheinlich hat der Server den Redirect auf 127.0.0.1 nicht erlaubt.")
        print("     Prüfe ob im Browser eine 'misconfigured-application'-Seite erschienen ist.")


if __name__ == "__main__":
    test_loopback_redirect()
