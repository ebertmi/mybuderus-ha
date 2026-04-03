# myBuderus API Spec

## Auth — SingleKey ID (OAuth2 PKCE)

- **Discovery URI:** https://singlekey-id.com/auth/
- **Authorization Endpoint:** https://singlekey-id.com/auth/connect/authorize
- **Token Endpoint:** https://singlekey-id.com/auth/connect/token
- **UserInfo Endpoint:** https://singlekey-id.com/auth/connect/userinfo
- **JWKS URI:** https://singlekey-id.com/auth/.well-known/openid-configuration/jwks
- **End Session Endpoint:** https://singlekey-id.com/auth/connect/endsession
- **Client ID:** 762162C0-FA2D-4540-AE66-6489F189FADC
- **Redirect URI (App):** com.buderus.tt.dashtt://app/login
- **Redirect URI (Prototyp):** http://localhost:8765/callback
- **Scopes:** openid email profile offline_access pointt.gateway.list pointt.gateway.resource.dashapp pointt.castt.flow.token-exchange bacon hcc.tariff.read
- **PKCE:** Code Challenge Method S256 (auch `plain` unterstützt; S256 bevorzugen)
- **Flow:** Authorization Code + PKCE (kein client_secret)
- **localhost-Redirect erlaubt:** NEIN — Server antwortet mit HTTP 302 → `misconfigured-application`-Fehlerseite. `http://localhost:8765/callback` ist beim Client nicht registriert. Nur `com.buderus.tt.dashtt://app/login` (Android Custom Scheme) ist als Redirect URI hinterlegt. Für den Prototyp muss entweder ein Custom URI Scheme simuliert werden (z.B. per lokaler URL-Handler-Registrierung) oder eine alternative Methode gewählt werden.

### Discovery-Rohdaten (relevante Felder)

```json
{
  "issuer": "https://singlekey-id.com/auth",
  "authorization_endpoint": "https://singlekey-id.com/auth/connect/authorize",
  "token_endpoint": "https://singlekey-id.com/auth/connect/token",
  "userinfo_endpoint": "https://singlekey-id.com/auth/connect/userinfo",
  "jwks_uri": "https://singlekey-id.com/auth/.well-known/openid-configuration/jwks",
  "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
  "response_types_supported": ["code", "code id_token"],
  "code_challenge_methods_supported": ["plain", "S256"],
  "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"]
}
```

**Hinweis zu `token_endpoint_auth_methods_supported`:** Der Server listet nur `client_secret_basic` und `client_secret_post` — kein `none`. Das bedeutet die Server-Konfiguration erwartet formal ein client_secret. Die App umgeht das vermutlich, indem sie ein leeres oder hartcodiertes secret sendet, oder der Server akzeptiert Requests ohne secret für diesen spezifischen Client. Muss beim Token-Exchange getestet werden.

## REST API

- **Base URL:** https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/
- **URL-Muster:** gateways/{gatewayId}/resource/{path}
- **Auth Header:** Authorization: Bearer {access_token}

## Bekannte Endpunkte

Alle Pfade relativ zu: `gateways/{gatewayId}/resource/`

| Datenpunkt | Pfad | Methode |
|---|---|---|
| Heizkreis Betriebsart | `heatingCircuits/hc1/operationMode` | GET | ✓ validiert |
| Heizkreis Solltemperatur | `heatingCircuits/hc1/currentRoomSetpoint` | GET | ✓ validiert |
| Heizkreis Raumtemperatur | `heatingCircuits/hc1/roomtemperature` | GET | ✓ validiert (kein Sensor → Sentinel -32768) |
| Warmwasser Betriebsart | `dhwCircuits/dhw1/operationMode` | GET | ✓ validiert |
| Warmwasser Speichertemperatur | `dhwCircuits/dhw1/actualTemp` | GET | ✓ validiert (RRC Provider) |
| Warmwasser Aktiver Sollwert | `dhwCircuits/dhw1/currentSetpoint` | GET | ✓ validiert (inkl. Legionellenschutz) |
| Warmwasser Solltemperatur (high) | `dhwCircuits/dhw1/temperatureLevels/high` | GET/PUT | ✓ validiert |
| Warmwasser Solltemperatur (low) | `dhwCircuits/dhw1/temperatureLevels/low` | GET/PUT | ✓ validiert |
| Außentemperatur | `system/sensors/temperatures/outdoor_t1` | GET | ✓ validiert |
| Vorlauftemperatur | `heatSources/actualSupplyTemperature` | GET | ✓ validiert |
| Rücklauftemperatur | `heatSources/returnTemperature` | GET | ✓ validiert |
| Kompressorstatus | `heatSources/compressor/status` | GET | ✓ validiert |
| Zuheizerstatus | `heatSources/Source/eHeater/status` | GET | ✓ validiert |
| System Saisonmodus | `system/seasonOptimizer/mode` | GET/PUT | ✗ null auf diesem Gateway |
| System Info | `system/info` | GET | ✓ validiert |
| Wärmequellen Info | `heatSources/info` | GET | ✓ validiert |
| Warmwasser Ist-Temperatur (ConnectKey) | `dhwCircuits/dhw1/currentTemperatureLevel` | GET | ✗ null / 403 (ConnectKey-spezifisch, nicht MX300) |
| Warmwasser Speichertemperatur (alt) | `dhwCircuits/dhw1/actualStorageTemperature` | GET | ✗ HTTP 403 |
| System Saisonmodus (alt) | `system/globalSeasonOptimizer/currentMode` | GET | nicht getestet |

## Validierte Response-Schemas (Live-Test HMC310/MX300)

### floatValue (Temperaturen, numerische Werte)

```json
{
  "id": "/heatSources/returnTemperature",
  "type": "floatValue",
  "writeable": 0,
  "state": [{"short": 32767.0}, {"open": -32768.0}],
  "unitOfMeasure": "C",
  "value": 45.4
}
```

**Sentinel-Werte** (im `state`-Array definiert, bedeuten "nicht verfügbar"):
- `-32768.0` → Sensor offen / nicht angeschlossen
- `32767.0` → Sensor Kurzschluss

### stringValue (Betriebsart, Status)

```json
{
  "id": "/heatSources/compressor/status",
  "type": "stringValue",
  "writeable": 0,
  "value": "dhw",
  "allowedValues": ["off", "heating", "cooling", "dhw", "pool", "pool_heat", "defrost", "alarm"]
}
```

### floatValue (schreibbar, mit min/max)

```json
{
  "id": "/dhwCircuits/dhw1/temperatureLevels/high",
  "type": "floatValue",
  "writeable": 1,
  "minValue": 30.0,
  "unitOfMeasure": "C",
  "value": 48.0,
  "maxValue": 48.0
}
```

## Echtzeit-Datenpunkte

Alle Pfade sind REST-Endpunkte relativ zu:
`https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/gateways/{gatewayId}/resource/`

Die Datenpunkte werden über **Standard Pointt REST API (GET)** abgerufen — kein MQTT, kein icom-Bulk.
Der icom-Bulk-Mechanismus (POST `bulk`) existiert ebenfalls, aber für die nachfolgenden Werte genügt jeweils ein einfacher GET.

| Datenpunkt | Quelle | Pfad |
|---|---|---|
| Außentemperatur | REST GET | `system/sensors/temperatures/outdoor_t1` |
| Kompressorstatus | REST GET | `heatSources/compressor/status` |
| Vorlauftemperatur | REST GET | `heatSources/actualSupplyTemperature` |
| Rücklauftemperatur | REST GET | `heatSources/returnTemperature` |
| Zuheizerstatus | REST GET | `heatSources/Source/eHeater/status` |
| Systemmodus | REST GET/PUT | `system/seasonOptimizer/mode` |

### Weitere gefundene Monitoring-Pfade (Wärmepumpe)

Aus `MyHeatPumpMonitoringBulkResource` und `MonitoringValuesBulkResource`:

| Datenpunkt | Pfad |
|---|---|
| Modulationsgrad Kompressor | `heatSources/actualModulation` |
| Systemdruck | `heatSources/systemPressure` |
| Sole-Vorlauf (Erdwärme) | `heatSources/hs1/brineCircuit/collectorOutflowTemp` |
| Sole-Rücklauf (Erdwärme) | `heatSources/hs1/brineCircuit/collectorInflowTemp` |
| Gesamtbetriebsstunden | `heatSources/workingTime/totalSystem` |
| Anzahl Starts | `heatSources/numberOfStarts` |
| Passive Kühlung Vorlauf | `heatSources/passiveCooling/inflowTemp` |
| Saisonmodus aktuell | `system/globalSeasonOptimizer/currentMode` |

### Technische Details zum icom-Bulk-Mechanismus

- GET: `gateways/{gatewayId}/resource{resourcePath}` (z.B. `gateways/{id}/resource/heatSources/returnTemperature`)
- POST `bulk`: Verwendet relative URL `"bulk"` — Basis-URL kommt vom konfigurierten HTTP-Client
- ConnectKey-Provider und icom-Provider verwenden dasselbe Schema

### Wichtige Hinweise

- Die PointtService-Klasse (Retrofit-Interface) bestätigt: `heatSources/returnTemperature` ist ein direkter GET-Endpunkt (Zeile 384)
- `system/sensors/temperatures/outdoor_t1` ist ebenfalls als direkter GET-Endpunkt vorhanden (Zeile 492)
- Heizkreis-Betriebsart erfolgt über `{circuitId}/operationMode` (z.B. `heatingCircuits/hc1/operationMode`)

## Gateway-Liste

**GET** `https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/gateways/`

Quelle: `GatewaysDataSourceImpl.getDevices()` verwendet relative URL `"gateways/"`.

Response-Schema (`PointtDevice`-Objekte, direkte Array-Antwort):

```json
[
  {
    "deviceId": "<string>",
    "gatewayPassword": "<string>",
    "userPassword": "<string>",
    "deviceType": "<string>",
    "brandId": "<string|null>",
    "firmwareVersion": "<string|null>",
    "hardwareVersion": "<string|null>",
    "productId": "<string|null>",
    "serialNumber": "<string|null>"
  }
]
```

**Wichtig:** Das Feld `deviceId` ist die Gateway-ID, die als `{gatewayId}` in allen weiteren API-Aufrufen verwendet wird.

## Bulk-Request (RRC/icom)

**POST** `https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/bulk`

Quelle: `RrcRemoteDataSourceImpl.postBulk()` verwendet relative URL `"bulk"`.

Request Body (`List<BulkBody>`):

```json
[
  {
    "gatewayId": "<deviceId aus Gateway-Liste>",
    "resourcePaths": [
      "/heatingCircuits/hc1/operationMode",
      "/system/sensors/temperatures/outdoor_t1"
    ]
  }
]
```

Response (`List<BulkResponse>`):

```json
[
  {
    "gatewayId": "<string>",
    "resourcePaths": [
      {
        "resourcePath": "/heatingCircuits/hc1/operationMode",
        "serverStatus": 200,
        "gatewayResponse": {
          "status": 200,
          "payload": { "value": "auto" }
        }
      },
      {
        "resourcePath": "/system/sensors/temperatures/outdoor_t1",
        "serverStatus": 200,
        "gatewayResponse": {
          "status": 200,
          "payload": { "value": -2.5 }
        }
      }
    ]
  }
]
```

**Hinweise:**
- `BulkBody` hat die Felder `gatewayId` (String) und `resourcePaths` (List&lt;String&gt;).
- `BulkResponse` hat die Felder `gatewayId` (String) und `resourcePaths` (List&lt;ResourcePath&gt;).
- `ResourcePath` hat die Felder `resourcePath` (String), `serverStatus` (Integer), `gatewayResponse` (GatewayResponse).
- `GatewayResponse` hat die Felder `status` (Integer) und `payload` (BulkPayload — sealed class mit Subtypen wie `StringValue`, `FloatValue`, `IntegerValue`, `RefEnum` usw.).
- Das `payload`-Objekt ist polymorph: je nach Datenpunkt wird ein anderer Subtyp zurückgegeben. Für einfache Werte (Temperatur, Betriebsart) sind `FloatValue` bzw. `StringValue` / `RefEnum` relevant.
