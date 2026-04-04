# myBuderus HA Custom Component — Design Spec

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Date:** 2026-04-04
**Status:** Approved

---

## Ziel

Eine Home Assistant Custom Component (`custom_components/mybuderus/`), die 14 Sensor-Entities aus der myBuderus/Bosch Wärmepumpen-API bereitstellt. Phase 3 des Projekts — nur lesend, keine Steuerung.

## Architektur

Eigenständiger async API-Client (`aiohttp`) ohne externe OAuth-Bibliotheken. Ein `DataUpdateCoordinator` pollt alle Datenpunkte per Bulk-Request. Kein Code-Sharing mit dem Prototyp — die Custom Component ist eigenständig.

**Tech Stack:** Python 3.12+, aiohttp (HA-intern), pytest + unittest.mock

---

## Dateistruktur

```
custom_components/mybuderus/
├── manifest.json        # HA Manifest
├── const.py             # Konstanten: URLs, Client-ID, Scopes, Sensor-Definitionen
├── auth.py              # OAuth2 PKCE: Code-Exchange, Token-Refresh (async)
├── api.py               # REST-Client: Bulk-Request, Gateway-Liste (async)
├── coordinator.py       # DataUpdateCoordinator: Polling, Token-Refresh-Logik
├── config_flow.py       # Config Flow (2-Schritte Auth) + Options Flow (Intervall)
├── sensor.py            # 14 Sensor-Entities
└── strings.json         # UI-Texte (deutsch)

tests/
└── components/
    └── mybuderus/
        ├── conftest.py
        ├── test_auth.py
        ├── test_api.py
        ├── test_coordinator.py
        └── test_config_flow.py
```

---

## Authentifizierung

### OAuth2 PKCE (SingleKey ID)

- **Client ID:** `762162C0-FA2D-4540-AE66-6489F189FADC`
- **Authorization Endpoint:** `https://singlekey-id.com/auth/connect/authorize`
- **Token Endpoint:** `https://singlekey-id.com/auth/connect/token`
- **Redirect URI:** `com.buderus.tt.dashtt://app/login` (einzige registrierte URI)
- **PKCE:** S256
- **Kein client_secret**

### Einschränkung

Kein automatischer Redirect-Capture möglich:
- `http://localhost` → abgelehnt (Fehlkonfigurierte Anwendung)
- `http://127.0.0.1` → abgelehnt
- Device Flow (RFC 8628) → nicht in `grant_types_supported`
- OOB (`urn:ietf:wg:oauth:2.0:oob`) → nicht unterstützt

**Lösung:** Manueller Copy-Paste-Flow im HA Config Flow.

### Token-Speicherung

Access Token + Refresh Token werden im HA Config Entry gespeichert (via `hass.config_entries` — HA verschlüsselt den Speicher). Zusätzlich `expires_at` (Unix-Timestamp) für Expiry-Check.

```python
# Config Entry Data (verschlüsselt):
{
    "access_token": "...",
    "refresh_token": "...",
    "expires_at": 1234567890.0,
    "gateway_id": "101739215"
}
```

---

## Config Flow

### Step 1 — Anmeldung (`step_id: "auth"`)

HA zeigt:
1. Beschreibungstext mit Schritt-für-Schritt-Anleitung:
   - "Klicke den Link unten um dich bei SingleKey ID anzumelden"
   - "Logge dich mit deinen Zugangsdaten ein"
   - "Nach dem Login erscheint eine Fehlerseite im Browser"
   - "Öffne die Browser-Entwicklerkonsole (F12) → Netzwerk-Tab → filtere nach `com.buderus`"
   - "Kopiere die vollständige URL oder nur den `code`-Parameter"
2. Klickbarer Auth-Link (generiert mit PKCE-Challenge)
3. Textfeld: "Redirect-URL oder Code einfügen"

Bei Eingabe:
- URL (`com.buderus...` oder `http...`) → Code per URL-Parsing extrahieren
- Nur Code → direkt verwenden
- Code gegen Token tauschen via `auth.py`
- Gateway-ID abrufen via `api.py`
- Bei Fehler: Fehlermeldung anzeigen, Schritt wiederholen

### Step 2 — Konfiguration (`step_id: "config"`)

- **Name:** Freitext, Default `"myBuderus"`
- **Polling-Intervall:** Integer (Sekunden), Default `300`, Min `30`

### Options Flow

Nachträgliche Änderung des Polling-Intervalls über HA Settings → Integrations → myBuderus → Konfigurieren.

### Re-Auth Flow

Wenn Token-Refresh fehlschlägt: HA-Notification + Re-Auth-Eintrag in der UI. User durchläuft Step 1 erneut.

---

## DataUpdateCoordinator

`coordinator.py` erbt von `DataUpdateCoordinator`. Bei jedem Update-Interval:

1. Prüfen ob `access_token` abgelaufen (`expires_at - 60s`)
2. Falls ja: Token-Refresh via `auth.py`
   - Erfolg: neues Token im Config Entry speichern
   - Fehler: Re-Auth auslösen, `UpdateFailed` werfen
3. Bulk-Request mit allen 14 Pfaden via `api.py`
4. Ergebnis als `dict[str, Any]` (Pfad → Payload) zurückgeben

```python
# Coordinator data structure:
{
    "/heatingCircuits/hc1/operationMode": {"value": "manual", ...},
    "/dhwCircuits/dhw1/actualTemp": {"value": 53.3, ...},
    # ... 12 weitere Pfade
}
```

---

## Sensor-Entities

`sensor.py` definiert 14 Entities über eine `SensorEntityDescription`-Liste in `const.py`.

| Entity-ID-Suffix | Name | API-Pfad | Einheit | Device Class |
|---|---|---|---|---|
| `hc_operation_mode` | Heizkreis Betriebsart | `heatingCircuits/hc1/operationMode` | — | `enum` |
| `hc_room_setpoint` | Heizkreis Solltemperatur | `heatingCircuits/hc1/currentRoomSetpoint` | °C | `temperature` |
| `hc_room_temperature` | Heizkreis Raumtemperatur | `heatingCircuits/hc1/roomtemperature` | °C | `temperature` |
| `dhw_operation_mode` | WW Betriebsart | `dhwCircuits/dhw1/operationMode` | — | `enum` |
| `dhw_actual_temp` | WW Speichertemperatur | `dhwCircuits/dhw1/actualTemp` | °C | `temperature` |
| `dhw_current_setpoint` | WW Aktiver Sollwert | `dhwCircuits/dhw1/currentSetpoint` | °C | `temperature` |
| `dhw_setpoint_high` | WW Sollwert high | `dhwCircuits/dhw1/temperatureLevels/high` | °C | `temperature` |
| `dhw_setpoint_low` | WW Sollwert low | `dhwCircuits/dhw1/temperatureLevels/low` | °C | `temperature` |
| `outdoor_temperature` | Außentemperatur | `system/sensors/temperatures/outdoor_t1` | °C | `temperature` |
| `compressor_status` | Kompressorstatus | `heatSources/compressor/status` | — | `enum` |
| `supply_temperature` | Vorlauftemperatur | `heatSources/actualSupplyTemperature` | °C | `temperature` |
| `return_temperature` | Rücklauftemperatur | `heatSources/returnTemperature` | °C | `temperature` |
| `backup_heater_status` | Zuheizerstatus | `heatSources/Source/eHeater/status` | — | `enum` |
| `system_mode` | Systemmodus | `system/seasonOptimizer/mode` | — | `enum` |

**Wert-Extraktion:**
- `floatValue` mit Sentinel (`-32768.0`, `32767.0` aus `state`-Array) → `None` → HA `unavailable`
- `stringValue` → `value`-Feld direkt
- API-Payload `None` (null-Response) → `None` → HA `unavailable`

Alle Entities gehören zu einem einzigen HA-Device "myBuderus" mit `gateway_id` als Identifier.

---

## Fehlerbehandlung

| Fehler | Verhalten |
|---|---|
| 401 Unauthorized | Token-Refresh → bei Erfolg Poll wiederholen, bei Fehler Re-Auth |
| 403 Forbidden (einzelner Pfad) | Betroffener Sensor `unavailable`, andere weiter verfügbar |
| Bulk-Request schlägt komplett fehl | Alle Sensoren `unavailable`, `UpdateFailed` |
| Netzwerkfehler / Timeout | `UpdateFailed` → HA-Standard-Retry |
| Refresh Token abgelaufen | Re-Auth Flow auslösen |

---

## Testing

Alle Tests mit `pytest` + `unittest.mock`. Keine echten API-Calls.

**test_auth.py**
- `exchange_code()`: Mock Token-Endpunkt-Response → prüfe Token-Struktur
- `refresh_token()`: Mock Refresh-Response → prüfe neues Token
- `refresh_token()` bei 401: prüfe Exception

**test_api.py**
- `get_gateways()`: Mock Response → prüfe `deviceId`-Extraktion
- `get_bulk()`: Mock Bulk-Response mit fixture-Daten aus Phase-2-Rohdaten → prüfe flache Ergebnisliste
- Sentinel-Wert `-32768.0` → prüfe `None`-Extraktion

**test_coordinator.py**
- Token abgelaufen → prüfe dass Refresh aufgerufen wird
- 401 → Refresh → erneuter Poll
- `UpdateFailed` bei Netzwerkfehler

**test_config_flow.py**
- Vollständiger Flow mit gemockten auth/api-Calls
- Ungültiger Code → Fehler-Step
- Options Flow: Intervall-Änderung

---

## Constraints

- Nur lesend — keine Schreib-Operationen in Phase 3
- Lokale Installation (kein HACS)
- Keine Veröffentlichung
- HA-Mindestversion: 2024.1 (für aktuelle `SensorEntityDescription` API)
