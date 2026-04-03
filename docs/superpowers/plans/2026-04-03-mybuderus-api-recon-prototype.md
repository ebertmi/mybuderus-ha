# myBuderus API-Rekonstruktion & Python-Prototyp — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die myBuderus REST-API vollständig dokumentieren und mit einem Python-Script alle 8 gewünschten Datenpunkte live abrufen.

**Architecture:** Phase 1 analysiert den dekompilierten APK-Code weiter, um fehlende Endpunkte zu ermitteln, und schreibt alles in `docs/api-spec.md`. Phase 2 implementiert einen Python-Prototyp, der OAuth2 PKCE + REST nutzt, um die Datenpunkte mit echten Credentials abzurufen und das API-Spec zu validieren.

**Tech Stack:** Python 3.11+, `httpx`, `authlib`, dekompilierter Java/Kotlin-Code im Ordner `com.buderus.tt.dashtt.apk_Decompiler.com/sources/`

---

## Datei-Übersicht

| Datei | Zweck |
|---|---|
| `docs/api-spec.md` | Vollständige API-Dokumentation (Auth, Endpunkte, Schemas) |
| `prototype/main.py` | Haupt-Script: Auth → Gateway-ID → Datenpunkte abrufen → Ausgabe |
| `prototype/auth.py` | OAuth2 PKCE Flow (Token holen, refreshen) |
| `prototype/api.py` | REST-Client (Gateway-ID, Bulk-Request, einzelne Endpunkte) |
| `prototype/requirements.txt` | Python-Dependencies |
| `prototype/config.example.env` | Beispiel-Konfiguration (Credentials, nie committen) |

---

## Phase 1: API-Rekonstruktion

### Task 1: OpenID Connect Discovery abrufen

**Files:**
- Modify: `docs/api-spec.md` (neu anlegen)

- [ ] **Step 1: Discovery-Dokument abrufen**

```bash
curl -s "https://singlekey-id.com/auth/.well-known/openid-configuration" | python3 -m json.tool
```

Erwartete Ausgabe: JSON mit `authorization_endpoint`, `token_endpoint`, `userinfo_endpoint`, `jwks_uri`, `grant_types_supported`, `response_types_supported`.

Notiere die Werte für `authorization_endpoint` und `token_endpoint`.

- [ ] **Step 2: Prüfen ob PKCE unterstützt wird**

In der Discovery-Ausgabe nach `code_challenge_methods_supported` suchen. Erwarteter Wert: `["S256"]` oder ähnlich.

- [ ] **Step 3: Prüfen ob localhost-Redirect erlaubt ist**

```bash
curl -v "https://singlekey-id.com/auth/oauth2/authorize?client_id=762162C0-FA2D-4540-AE66-6489F189FADC&response_type=code&redirect_uri=http%3A%2F%2Flocalhost%3A8765%2Fcallback&scope=openid&code_challenge=abc&code_challenge_method=S256" 2>&1 | head -30
```

Prüfe ob der Server mit einem `redirect_uri_mismatch`-Fehler oder mit einer Login-Seite antwortet. Das entscheidet ob wir localhost als Redirect nutzen können.

- [ ] **Step 4: Ergebnisse in api-spec.md schreiben**

Erstelle `docs/api-spec.md` mit folgendem Inhalt (Werte aus Step 1/2 eintragen):

```markdown
# myBuderus API Spec

## Auth — SingleKey ID (OAuth2 PKCE)

- **Discovery URI:** https://singlekey-id.com/auth/
- **Authorization Endpoint:** <WERT AUS DISCOVERY>
- **Token Endpoint:** <WERT AUS DISCOVERY>
- **Client ID:** 762162C0-FA2D-4540-AE66-6489F189FADC
- **Redirect URI (App):** com.buderus.tt.dashtt://app/login
- **Redirect URI (Prototyp):** http://localhost:8765/callback
- **Scopes:** openid email profile offline_access pointt.gateway.list pointt.gateway.resource.dashapp pointt.castt.flow.token-exchange bacon hcc.tariff.read
- **PKCE:** Code Challenge Method S256
- **Flow:** Authorization Code + PKCE (kein client_secret)

## REST API

- **Base URL:** https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/
- **URL-Muster:** gateways/{gatewayId}/resource/{path}
- **Auth Header:** Authorization: Bearer {access_token}
```

- [ ] **Step 5: Commit**

```bash
git init  # falls noch nicht initialisiert
git add docs/api-spec.md
git commit -m "docs: add api-spec with auth discovery results"
```

---

### Task 2: DHW-Temperatur-Endpunkt ermitteln

**Files:**
- Lese: `com.buderus.tt.dashtt.apk_Decompiler.com/sources/com/bosch/tt/dashtt/kmpcore/data/source/remote/pointt/circuits/DhwCircuitsDataSourceImpl.java`
- Modify: `docs/api-spec.md`

- [ ] **Step 1: DhwCircuitsDataSourceImpl analysieren**

```bash
grep -n "currentTemperature\|temperatureLevel\|currentTemp\|dhw\|\"dhw\|path\|buildBase" \
  "com.buderus.tt.dashtt.apk_Decompiler.com/sources/com/bosch/tt/dashtt/kmpcore/data/source/remote/pointt/circuits/DhwCircuitsDataSourceImpl.java" \
  | grep -v "import\|package\|class\|Impl\|boolean\|throw" | head -30
```

Erwartete Ausgabe: Zeilen mit Pfad-Strings wie `"dhwCircuits/"` + `"/currentTemperatureLevel"` o.ä.

- [ ] **Step 2: DHW-Betriebsart-Pfad prüfen**

```bash
grep -n "getCircuitOperationMode\|operationMode\|OperationMode" \
  "com.buderus.tt.dashtt.apk_Decompiler.com/sources/com/bosch/tt/dashtt/kmpcore/data/source/remote/pointt/circuits/DhwCircuitsDataSourceImpl.java" \
  | head -20
```

- [ ] **Step 3: DHW-Datenpunkte in api-spec.md ergänzen**

Füge in `docs/api-spec.md` den Abschnitt "Bekannte Endpunkte" ein:

```markdown
## Bekannte Endpunkte

Alle Pfade relativ zu: `gateways/{gatewayId}/resource/`

| Datenpunkt | Pfad | Methode |
|---|---|---|
| Heizkreis Betriebsart | `heatingCircuits/hc1/operationMode` | GET |
| Heizkreis Solltemperatur | `heatingCircuits/hc1/currentRoomSetpoint` | GET |
| Heizkreis Raumtemperatur | `heatingCircuits/hc1/roomtemperature` | GET |
| Warmwasser Betriebsart | `dhwCircuits/dhw1/operationMode` | GET |
| Warmwasser Ist-Temperatur | `dhwCircuits/dhw1/<WERT AUS ANALYSE>` | GET |
| System Info | `system/info` | GET |
| Wärmequellen Info | `heatSources/info` | GET |
```

- [ ] **Step 4: Commit**

```bash
git add docs/api-spec.md
git commit -m "docs: add DHW endpoint analysis"
```

---

### Task 3: Echtzeit-Datenpunkte ermitteln (Outdoor, Kompressor, Vor-/Rücklauf)

**Files:**
- Lese: `com.buderus.tt.dashtt.apk_Decompiler.com/sources/com/bosch/tt/dashtt/icomprovider/data/local/model/heatsources/LocalIcomHeatSources.java`
- Suche: icom remote resources für HeatSources

- [ ] **Step 1: LocalIcomHeatSources-Felder vollständig auflisten**

```bash
grep -n "private\|public.*get\|LocalFloat\|LocalString\|LocalBool" \
  "com.buderus.tt.dashtt.apk_Decompiler.com/sources/com/bosch/tt/dashtt/icomprovider/data/local/model/heatsources/LocalIcomHeatSources.java" \
  | grep -v "import\|package\|class\|Companion\|realm\|kotlin\|boolean r\|Object r" | head -40
```

Erwartete Ausgabe: Liste aller Felder wie `outdoorTemperature`, `compressorActivity`, `flowTemperature`, `returnTemperature`, etc.

- [ ] **Step 2: IcomHeatSourcesResource-Pfade finden**

```bash
find "com.buderus.tt.dashtt.apk_Decompiler.com/sources" -name "*HeatSource*Resource*" | grep -v "\$\|Factory"
```

Falls gefunden:
```bash
grep -n "getPath\|path\|return\|\"hs\|\"heat" <GEFUNDENE_DATEI> | head -20
```

- [ ] **Step 3: MQTT-Topic-Format ermitteln (falls Echtzeit-Daten via MQTT)**

```bash
find "com.buderus.tt.dashtt.apk_Decompiler.com/sources/com/bosch/tt/dashtt" \
  -name "*.java" | xargs grep -l "topic\|Topic\|subscribe\|Subscribe" 2>/dev/null \
  | grep -v "hivemq\|okhttp\|firebase" | head -10
```

Für jede gefundene Datei:
```bash
grep -n "\"topic\|topic/\|Topic\|subscribe\|publish" <DATEI> | grep -v "import\|class\|boolean\|throw" | head -20
```

- [ ] **Step 4: Echtzeit-Endpunkte in api-spec.md ergänzen**

Füge in `docs/api-spec.md` ein:

```markdown
## Echtzeit-Datenpunkte

| Datenpunkt | Quelle | Pfad/Topic |
|---|---|---|
| Außentemperatur | <REST oder MQTT> | <WERT AUS ANALYSE> |
| Kompressorleistung | <REST oder MQTT> | <WERT AUS ANALYSE> |
| Vorlauftemperatur | <REST oder MQTT> | <WERT AUS ANALYSE> |
| Rücklauftemperatur | <REST oder MQTT> | <WERT AUS ANALYSE> |
| Zuheizerstatus | <REST oder MQTT> | <WERT AUS ANALYSE> |
| Systemmodus | <REST oder MQTT> | <WERT AUS ANALYSE> |
```

- [ ] **Step 5: Commit**

```bash
git add docs/api-spec.md
git commit -m "docs: add realtime data endpoint analysis"
```

---

### Task 4: Bulk-Request-Format und Gateway-List-Endpunkt dokumentieren

**Files:**
- Suche: `BulkBody.java`, `BulkResponse.java`, `GatewaysDataSourceImpl.java`

- [ ] **Step 1: Bulk-Body-Schema ermitteln**

```bash
find "com.buderus.tt.dashtt.apk_Decompiler.com/sources" -name "BulkBody*" | grep -v "\$\|Factory"
```

```bash
grep -n "String\|List\|body\|path\|url\|resource\|private\|public" <GEFUNDENE_DATEI> \
  | grep -v "import\|package\|class\|kotlin\|boolean r\|Object r\|Intrinsics" | head -30
```

- [ ] **Step 2: Bulk-Response-Schema ermitteln**

```bash
find "com.buderus.tt.dashtt.apk_Decompiler.com/sources" -name "BulkResponse*" | grep -v "\$\|Factory"
grep -n "String\|value\|body\|status\|private\|public" <GEFUNDENE_DATEI> \
  | grep -v "import\|package\|class\|kotlin\|boolean r\|Object r\|Intrinsics" | head -30
```

- [ ] **Step 3: Gateway-List-Endpunkt ermitteln**

```bash
grep -n "gateway\|getDevices\|path\|url\|buildBase" \
  "com.buderus.tt.dashtt.apk_Decompiler.com/sources/com/bosch/tt/dashtt/kmpcore/data/source/remote/pointt/devices/GatewaysDataSourceImpl.java" \
  | grep -v "import\|package\|class\|boolean\|throw\|Intrinsics" | head -20
```

- [ ] **Step 4: Bulk + Gateway in api-spec.md ergänzen**

Füge in `docs/api-spec.md` ein:

```markdown
## Gateway-Liste

**GET** `https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/gateways`

Response (Schema aus Analyse):
```json
{
  "gateways": [
    {
      "gatewayId": "<ID>",
      ...
    }
  ]
}
```

## Bulk-Request

**POST** `gateways/{gatewayId}/resource/bulk`

Request Body:
```json
[
  {"url": "/heatingCircuits/hc1/operationMode"},
  {"url": "/dhwCircuits/dhw1/operationMode"}
]
```

Response:
```json
[
  {"url": "/heatingCircuits/hc1/operationMode", "body": {"value": "auto", "unitOfMeasure": null}},
  {"url": "/dhwCircuits/dhw1/operationMode", "body": {"value": "on", "unitOfMeasure": null}}
]
```
```

- [ ] **Step 5: Commit**

```bash
git add docs/api-spec.md
git commit -m "docs: add bulk request format and gateway list endpoint"
```

---

## Phase 2: Python-Prototyp

### Task 5: Projekt-Setup

**Files:**
- Create: `prototype/requirements.txt`
- Create: `prototype/config.example.env`
- Create: `prototype/.gitignore`

- [ ] **Step 1: Verzeichnis anlegen**

```bash
mkdir -p prototype
```

- [ ] **Step 2: requirements.txt erstellen**

Inhalt von `prototype/requirements.txt`:

```
httpx==0.27.0
authlib==1.3.0
python-dotenv==1.0.1
```

- [ ] **Step 3: config.example.env erstellen**

Inhalt von `prototype/config.example.env`:

```env
# Kopiere diese Datei nach prototype/.env und trage deine Daten ein
SINGLEKEY_USERNAME=deine@email.com
SINGLEKEY_PASSWORD=deinPasswort
```

- [ ] **Step 4: .gitignore für Credentials erstellen**

Inhalt von `prototype/.gitignore`:

```
.env
*.env
__pycache__/
*.pyc
token_cache.json
```

- [ ] **Step 5: Dependencies installieren**

```bash
cd prototype
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Erwartete Ausgabe: `Successfully installed httpx-0.27.0 authlib-1.3.0 python-dotenv-1.0.1` (und Abhängigkeiten).

- [ ] **Step 6: Commit**

```bash
cd ..
git add prototype/requirements.txt prototype/config.example.env prototype/.gitignore
git commit -m "feat: add prototype project setup"
```

---

### Task 6: OAuth2 PKCE Auth implementieren

**Files:**
- Create: `prototype/auth.py`

- [ ] **Step 1: auth.py mit PKCE-Flow erstellen**

Inhalt von `prototype/auth.py`:

```python
"""
OAuth2 PKCE Auth für SingleKey ID.
Öffnet einen Browser für den Login und fängt den Callback via lokalem HTTP-Server ab.
"""
import base64
import hashlib
import json
import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

# Konstanten aus auth_config_production.json
CLIENT_ID = "762162C0-FA2D-4540-AE66-6489F189FADC"
DISCOVERY_URI = "https://singlekey-id.com/auth/"
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
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
TOKEN_CACHE_FILE = Path(__file__).parent / "token_cache.json"


def _generate_pkce_pair() -> tuple[str, str]:
    """Gibt (code_verifier, code_challenge) zurück."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def _fetch_oidc_config() -> dict:
    """Lädt das OpenID Connect Discovery-Dokument."""
    url = DISCOVERY_URI.rstrip("/") + "/.well-known/openid-configuration"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _exchange_code_for_token(code: str, code_verifier: str, token_endpoint: str) -> dict:
    """Tauscht den Authorization Code gegen Access + Refresh Token."""
    resp = httpx.post(
        token_endpoint,
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


def _refresh_access_token(refresh_token: str, token_endpoint: str) -> dict:
    """Erneuert den Access Token via Refresh Token."""
    resp = httpx.post(
        token_endpoint,
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": refresh_token,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _save_token_cache(token_data: dict) -> None:
    token_data["cached_at"] = time.time()
    TOKEN_CACHE_FILE.write_text(json.dumps(token_data, indent=2))


def _load_token_cache() -> dict | None:
    if not TOKEN_CACHE_FILE.exists():
        return None
    try:
        return json.loads(TOKEN_CACHE_FILE.read_text())
    except Exception:
        return None


def _is_token_expired(token_data: dict) -> bool:
    cached_at = token_data.get("cached_at", 0)
    expires_in = token_data.get("expires_in", 3600)
    return time.time() > cached_at + expires_in - 60  # 60s Puffer


def get_access_token() -> str:
    """
    Gibt einen gültigen Access Token zurück.
    Nutzt Cache wenn möglich, refresht wenn abgelaufen, startet sonst Browser-Login.
    """
    oidc_config = _fetch_oidc_config()
    token_endpoint = oidc_config["token_endpoint"]
    authorization_endpoint = oidc_config["authorization_endpoint"]

    # Cache prüfen
    cached = _load_token_cache()
    if cached:
        if not _is_token_expired(cached):
            print("✓ Nutze gecachten Access Token.")
            return cached["access_token"]
        if cached.get("refresh_token"):
            print("↻ Access Token abgelaufen, refreshe...")
            try:
                new_token = _refresh_access_token(cached["refresh_token"], token_endpoint)
                _save_token_cache(new_token)
                return new_token["access_token"]
            except Exception as e:
                print(f"  Refresh fehlgeschlagen ({e}), starte neu...")

    # Neuer Login via Browser
    print("🔐 Starte OAuth2 PKCE Login...")
    code_verifier, code_challenge = _generate_pkce_pair()

    auth_params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "login",
    }
    auth_url = authorization_endpoint + "?" + urlencode(auth_params)

    # Lokalen HTTP-Server starten um Callback abzufangen
    auth_code_container = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/callback":
                params = parse_qs(parsed.query)
                if "code" in params:
                    auth_code_container["code"] = params["code"][0]
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"<h1>Login erfolgreich! Du kannst dieses Fenster schliessen.</h1>")
                else:
                    error = params.get("error", ["unbekannt"])[0]
                    auth_code_container["error"] = error
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(f"<h1>Fehler: {error}</h1>".encode())

        def log_message(self, format, *args):
            pass  # Kein Log-Spam

    server = HTTPServer(("localhost", REDIRECT_PORT), CallbackHandler)
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.daemon = True
    server_thread.start()

    print(f"  Öffne Browser: {auth_url[:80]}...")
    webbrowser.open(auth_url)

    print("  Warte auf Callback (max. 120s)...")
    server_thread.join(timeout=120)

    if "error" in auth_code_container:
        raise RuntimeError(f"Auth fehlgeschlagen: {auth_code_container['error']}")
    if "code" not in auth_code_container:
        raise RuntimeError("Kein Authorization Code erhalten (Timeout?)")

    token_data = _exchange_code_for_token(
        auth_code_container["code"], code_verifier, token_endpoint
    )
    _save_token_cache(token_data)
    print("✓ Login erfolgreich, Token gecacht.")
    return token_data["access_token"]


if __name__ == "__main__":
    token = get_access_token()
    print(f"\nAccess Token (ersten 40 Zeichen): {token[:40]}...")
```

- [ ] **Step 2: Auth manuell testen**

```bash
cd prototype
source .venv/bin/activate
python auth.py
```

Erwartete Ausgabe: Browser öffnet sich mit SingleKey ID Login-Seite. Nach Login: `✓ Login erfolgreich, Token gecacht.` und Token-Vorschau.

Falls `redirect_uri_mismatch`-Fehler: In `api-spec.md` notieren dass localhost-Redirect nicht erlaubt ist und Alternative evaluieren (z.B. manuelle Code-Eingabe).

- [ ] **Step 3: Commit**

```bash
cd ..
git add prototype/auth.py
git commit -m "feat: add OAuth2 PKCE auth module"
```

---

### Task 7: API-Client implementieren

**Files:**
- Create: `prototype/api.py`

- [ ] **Step 1: api.py erstellen**

Inhalt von `prototype/api.py`:

```python
"""
myBuderus REST API Client.
Nutzt die Pointt-API von Bosch/Buderus.
"""
from typing import Any

import httpx

BASE_URL = "https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/"


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def get_gateways(access_token: str) -> list[dict]:
    """
    Gibt die Liste aller Gateways (Geräte) des Accounts zurück.
    Jeder Eintrag enthält mindestens eine 'gatewayId'.
    """
    resp = httpx.get(
        BASE_URL + "gateways",
        headers=_headers(access_token),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"  Gateway-Response: {data}")  # Debugging: zeigt echte Struktur
    # Schema wird nach erstem echten Call angepasst
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Versuche bekannte Schlüssel
        for key in ("gateways", "items", "devices"):
            if key in data:
                return data[key]
    return [data]


def get_resource(access_token: str, gateway_id: str, path: str) -> Any:
    """
    Ruft einen einzelnen Endpunkt ab.
    path z.B. 'heatingCircuits/hc1/operationMode'
    """
    url = BASE_URL + f"gateways/{gateway_id}/resource/{path}"
    resp = httpx.get(url, headers=_headers(access_token), timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_bulk(access_token: str, gateway_id: str, paths: list[str]) -> list[dict]:
    """
    Ruft mehrere Endpunkte in einer Anfrage ab (Bulk).
    paths: Liste von Pfad-Strings, z.B. ['heatingCircuits/hc1/operationMode', ...]
    Gibt Liste von Dicts zurück: [{'url': '...', 'body': {...}}, ...]
    """
    body = [{"url": f"/{path}"} for path in paths]
    url = BASE_URL + f"gateways/{gateway_id}/resource/bulk"
    resp = httpx.post(url, headers=_headers(access_token), json=body, timeout=20)

    if resp.status_code == 404:
        # Bulk nicht unterstützt — einzeln abrufen
        print("  Bulk-Endpunkt nicht verfügbar, falle zurück auf Einzel-Requests...")
        results = []
        for path in paths:
            try:
                data = get_resource(access_token, gateway_id, path)
                results.append({"url": f"/{path}", "body": data})
            except httpx.HTTPStatusError as e:
                results.append({"url": f"/{path}", "body": None, "error": str(e)})
        return results

    resp.raise_for_status()
    return resp.json()
```

- [ ] **Step 2: api.py manuell testen (Gateway-Liste)**

```bash
cd prototype
source .venv/bin/activate
python -c "
from auth import get_access_token
from api import get_gateways
token = get_access_token()
gateways = get_gateways(token)
print('Gateways:', gateways)
"
```

Erwartete Ausgabe: Liste mit mindestens einem Gateway-Objekt. Notiere die `gatewayId` für den nächsten Schritt. Passe `get_gateways()` an die echte Response-Struktur an und aktualisiere `docs/api-spec.md` mit dem echten Schema.

- [ ] **Step 3: Commit**

```bash
cd ..
git add prototype/api.py
git commit -m "feat: add REST API client module"
```

---

### Task 8: Haupt-Script implementieren und alle Datenpunkte abrufen

**Files:**
- Create: `prototype/main.py`

- [ ] **Step 1: main.py erstellen**

Inhalt von `prototype/main.py`:

```python
"""
myBuderus Prototyp — ruft alle gewünschten Datenpunkte ab und gibt sie aus.
"""
from auth import get_access_token
from api import get_bulk, get_gateways

# Alle gewünschten Endpunkte (Pfade relativ zu gateways/{id}/resource/)
# Passe diese Liste nach Task 2-4 (APK-Analyse) an!
RESOURCE_PATHS = [
    "heatingCircuits/hc1/operationMode",
    "heatingCircuits/hc1/currentRoomSetpoint",
    "heatingCircuits/hc1/roomtemperature",
    "dhwCircuits/dhw1/operationMode",
    "dhwCircuits/dhw1/currentTemperatureLevel",  # Ggf. Pfad anpassen nach Task 2
    "system/info",
    "heatSources/info",
    "heatSources/hs1/type",
]

# Lesbaren Namen zu Pfaden zuordnen
PATH_LABELS = {
    "heatingCircuits/hc1/operationMode": "Heizkreis Betriebsart",
    "heatingCircuits/hc1/currentRoomSetpoint": "Heizkreis Solltemperatur",
    "heatingCircuits/hc1/roomtemperature": "Heizkreis Raumtemperatur",
    "dhwCircuits/dhw1/operationMode": "Warmwasser Betriebsart",
    "dhwCircuits/dhw1/currentTemperatureLevel": "Warmwasser Ist-Temperatur",
    "system/info": "System Info",
    "heatSources/info": "Wärmequellen Info",
    "heatSources/hs1/type": "Wärmequellen Typ",
}


def extract_value(body: dict | None) -> str:
    """Extrahiert den Anzeigewert aus einer API-Response."""
    if body is None:
        return "N/A"
    if isinstance(body, dict):
        for key in ("value", "currentValue", "body", "data"):
            if key in body:
                val = body[key]
                unit = body.get("unitOfMeasure", "")
                return f"{val} {unit}".strip() if unit else str(val)
    return str(body)


def main():
    print("=== myBuderus Datenpunkte ===\n")

    print("1. Authentifizierung...")
    token = get_access_token()

    print("\n2. Gateway-ID ermitteln...")
    gateways = get_gateways(token)
    if not gateways:
        print("FEHLER: Keine Gateways gefunden!")
        return
    gateway = gateways[0]
    # Passe den Schlüssel nach Task 7 Step 2 an
    gateway_id = gateway.get("gatewayId") or gateway.get("id") or gateway.get("serialId")
    print(f"   Gateway-ID: {gateway_id}")

    print("\n3. Datenpunkte abrufen...")
    results = get_bulk(token, gateway_id, RESOURCE_PATHS)

    print("\n=== Ergebnisse ===")
    for item in results:
        path = item.get("url", "").lstrip("/")
        body = item.get("body")
        error = item.get("error")
        label = PATH_LABELS.get(path, path)

        if error:
            print(f"  ✗ {label}: FEHLER — {error}")
        else:
            value = extract_value(body)
            print(f"  ✓ {label}: {value}")

    print("\n=== Rohdaten (für api-spec.md) ===")
    for item in results:
        print(f"  {item.get('url')}: {item.get('body')}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Prototyp ausführen**

```bash
cd prototype
source .venv/bin/activate
python main.py
```

Erwartete Ausgabe: Alle Datenpunkte mit Werten. Notiere die Rohdaten und passe `docs/api-spec.md` mit echten Response-Schemas an.

Falls ein Endpunkt 404 zurückgibt: Pfad in RESOURCE_PATHS anpassen und api-spec.md korrigieren.

- [ ] **Step 3: api-spec.md mit echten Response-Schemas finalisieren**

Füge für jeden Endpunkt ein echtes Beispiel-Response-Schema in `docs/api-spec.md` ein, basierend auf den Rohdaten aus Step 2. Beispiel:

```markdown
### GET heatingCircuits/hc1/operationMode

Response:
```json
{
  "value": "auto",
  "allowedValues": ["auto", "manual", "off"],
  "unitOfMeasure": null
}
```
```

- [ ] **Step 4: Commit**

```bash
cd ..
git add prototype/main.py docs/api-spec.md
git commit -m "feat: add prototype main script and finalize api-spec"
```

---

### Task 9: Echtzeit-Datenpunkte integrieren

> Diesen Task erst ausführen nachdem Task 3 (APK-Analyse Echtzeit) abgeschlossen ist und die Endpunkte bekannt sind.

**Files:**
- Modify: `prototype/main.py`
- Modify: `docs/api-spec.md`

- [ ] **Step 1: Echtzeit-Pfade in RESOURCE_PATHS ergänzen**

Füge in `prototype/main.py` die in Task 3 ermittelten Pfade hinzu:

```python
RESOURCE_PATHS = [
    # ... bestehende Pfade ...
    "<OUTDOOR_TEMP_PFAD>",     # aus Task 3
    "<COMPRESSOR_PFAD>",       # aus Task 3
    "<FLOW_TEMP_PFAD>",        # aus Task 3
    "<RETURN_TEMP_PFAD>",      # aus Task 3
    "<BACKUP_HEATER_PFAD>",    # aus Task 3
    "<SYSTEM_MODE_PFAD>",      # aus Task 3
]
```

Ersetze `<..._PFAD>` durch die echten Pfade aus Task 3.

- [ ] **Step 2: Prototyp erneut ausführen**

```bash
cd prototype
source .venv/bin/activate
python main.py
```

Erwartete Ausgabe: Alle 10 Datenpunkte (8 + System Info + Wärmequellen Typ) mit Werten.

- [ ] **Step 3: Finale api-spec.md committen**

```bash
cd ..
git add prototype/main.py docs/api-spec.md
git commit -m "feat: add realtime datapoints to prototype, finalize api-spec"
```

---

## Selbst-Prüfung (nach Abschluss beider Phasen)

- [ ] `docs/api-spec.md` enthält alle Auth-Parameter, alle Endpunkte mit echten Response-Schemas
- [ ] `python main.py` läuft ohne Fehler durch und gibt alle 8 gewünschten Datenpunkte aus
- [ ] Kein `.env`-File committed (prüfen mit `git log --oneline -- prototype/.env`)
- [ ] Token-Cache (`token_cache.json`) ist in `.gitignore`
