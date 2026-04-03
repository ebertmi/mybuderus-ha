# myBuderus Home Assistant Integration — Design Spec

**Date:** 2026-04-03  
**Status:** Approved

---

## Ziel

Eine Home Assistant Custom Component, die statische und Echtzeit-Daten der myBuderus App (Bosch Wärmepumpe) im HA Dashboard anzeigt. Im ersten Schritt nur lesend (Sensoren), kein Schreiben/Steuern.

**Gewünschte Datenpunkte:**
- Heizkreis: Temperatur, Betriebsart
- Warmwasser: Temperatur, Betriebsart
- Echtzeit: Systemmodus, Außentemperatur, Kompressorleistung, Zuheizerstatus, Vorlauftemperatur, Rücklauftemperatur

---

## Phasen

### Phase 1 — API-Rekonstruktion

Ziel: Vollständige API-Dokumentation als `docs/api-spec.md`, ermittelt durch APK-Analyse des dekompilierten Quellcodes.

**Was wir bereits wissen:**

#### Auth — SingleKey ID (OAuth2 PKCE)
- Discovery URI: `https://singlekey-id.com/auth/`
- Client ID: `762162C0-FA2D-4540-AE66-6489F189FADC`
- Redirect URI: `com.buderus.tt.dashtt://app/login`
- Flow: Authorization Code mit PKCE (kein client_secret — mobile App)
- Scopes: `openid email profile offline_access pointt.gateway.list pointt.gateway.resource.dashapp pointt.castt.flow.token-exchange bacon hcc.tariff.read`
- Custom CA: `assets/auth/skid-root-certificate.cer`

#### REST API
- Production Base URL: `https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/`
- Dev Base URL: `https://pointt-dev.bosch-thermotechnology.com/pointt-api/api/v1/`
- URL-Muster: `gateways/{gatewayId}/resource/{path}`
- Bulk-Endpunkt: `POST gateways/{gatewayId}/resource/bulk`

#### Bekannte Endpunkte

| Datenpunkt | Pfad |
|---|---|
| Heizkreis Betriebsart | `heatingCircuits/hc1/operationMode` |
| Heizkreis Solltemperatur | `heatingCircuits/hc1/currentRoomSetpoint` |
| Heizkreis Raumtemperatur | `heatingCircuits/hc1/roomtemperature` |
| Heizkreis Temperaturlevel | `heatingCircuits/hc1/temperatureLevels` |
| Warmwasser Betriebsart | `dhwCircuits/dhw1/operationMode` |
| Warmwasser Temperatur | `dhwCircuits/dhw1/...` (noch zu ermitteln) |
| System Info | `system/info` |
| Wärmequellen Info | `heatSources/info` |
| Wärmequellen Typ | `heatSources/hs1/type` |

#### Noch zu ermitteln (in Phase 1)
- Außentemperatur: REST-Endpunkt oder MQTT-Topic
- Kompressorleistung/-status: REST-Endpunkt oder MQTT-Topic
- Vorlauf-/Rücklauftemperatur: vermutlich in `heatSources/` oder via MQTT
- Zuheizerstatus: REST-Endpunkt oder MQTT-Topic
- Warmwasser-Ist-Temperatur: genaue Unterressource von `dhwCircuits/dhw1/`
- Bulk-Request-Body-Schema
- Token-Exchange-Flow (Scope `pointt.castt.flow.token-exchange`)
- Gateway-ID abrufen: `gateways/` List-Endpunkt

**Aufgaben Phase 1:**
1. OpenID Connect Discovery abrufen → Token-Endpunkte dokumentieren
2. APK-Analyse vertiefen: DHW-Temperaturendpunkt, HeatSources-Felder, MQTT-Topic-Format
3. Response-Schemas für alle Endpunkte dokumentieren
4. Bulk-Request-Format dokumentieren
5. Gateway-List-Endpunkt dokumentieren

**Output:** `docs/api-spec.md`

---

### Phase 2 — Python-Prototyp

Ziel: Python-Script `prototype/main.py`, das sich authentifiziert und alle 8 Datenpunkte abruft und im Terminal ausgibt. Validiert das API-Spec mit echten Daten.

**Stack:**
- Python 3.11+
- `requests` oder `httpx` für HTTP
- `authlib` oder manuelle PKCE-Implementierung für OAuth2
- Kein HA-spezifischer Code

**Ablauf:**
1. OAuth2 PKCE Login mit Benutzer-Credentials (Username/Passwort via Browser-Flow oder Device-Flow)
2. Access Token erhalten
3. Gateway-ID abrufen
4. Bulk-Request für alle relevanten Endpunkte
5. Daten im Terminal ausgeben (strukturiert, alle 8 Datenpunkte)

**Output:** Lauffähiges Script + validiertes `docs/api-spec.md`

---

### Phase 3 — Home Assistant Custom Component

Ziel: `custom_components/mybuderus/` installierbar als HA Custom Component, zeigt alle 8 Datenpunkte als Sensor-Entities.

**Architektur:**
```
custom_components/mybuderus/
├── __init__.py          # Setup, DataUpdateCoordinator
├── config_flow.py       # UI-Konfiguration (Username, Passwort)
├── sensor.py            # Sensor-Entities (8 Sensoren)
├── api.py               # API-Client (Auth + REST)
├── const.py             # Konstanten (URLs, Scopes, etc.)
└── manifest.json        # HA Manifest
```

**Sensor-Entities:**

| Entity ID | Name | Einheit |
|---|---|---|
| `sensor.mybuderus_hc_operation_mode` | Heizkreis Betriebsart | — |
| `sensor.mybuderus_hc_temperature` | Heizkreis Temperatur | °C |
| `sensor.mybuderus_dhw_operation_mode` | Warmwasser Betriebsart | — |
| `sensor.mybuderus_dhw_temperature` | Warmwasser Temperatur | °C |
| `sensor.mybuderus_system_mode` | Systemmodus | — |
| `sensor.mybuderus_outdoor_temperature` | Außentemperatur | °C |
| `sensor.mybuderus_compressor_activity` | Kompressorleistung | % |
| `sensor.mybuderus_supply_temperature` | Vorlauftemperatur | °C |
| `sensor.mybuderus_return_temperature` | Rücklauftemperatur | °C |
| `sensor.mybuderus_backup_heater_status` | Zuheizerstatus | — |

**Polling:** Standard 5 Minuten, konfigurierbar  
**Auth:** Token-Refresh automatisch via Coordinator  
**Config Flow:** Username + Passwort (OAuth2 Resource Owner Password oder PKCE-Flow via eingebettetem Browser — abhängig von Phase-2-Erkenntnissen)

---

## Offene Fragen (werden in Phase 1/2 geklärt)

1. Unterstützt SingleKey ID den Resource Owner Password Credentials Flow (ROPC) für Username/Passwort direkt, oder ist ein Browser-basierter Flow nötig?
2. Kommen Echtzeit-Daten (Kompressor, Temperaturen) per REST-Polling oder MQTT?
3. Wie ist das Token-Exchange-Flow (`pointt.castt.flow.token-exchange`) strukturiert?
4. Gibt es Rate-Limiting auf der API?

---

## Constraints

- Nur lesend (Phase 1-3): keine Steuerung
- Keine Veröffentlichung auf HACS in Phase 3 (lokale Installation)
- APK-Analyse nur für Interoperabilität / Eigennutzung
