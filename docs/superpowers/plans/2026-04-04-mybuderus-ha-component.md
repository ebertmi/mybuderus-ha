# myBuderus HA Custom Component Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine installierbare HA Custom Component `custom_components/mybuderus/` mit 14 Sensor-Entities für die Bosch/Buderus Wärmepumpen-API.

**Architecture:** Eigenständiger async API-Client (`aiohttp`) ohne externe OAuth-Bibliotheken. Ein `DataUpdateCoordinator` pollt alle Datenpunkte per Bulk-Request. Manueller Copy-Paste OAuth2-PKCE-Flow im Config Flow, da der Auth-Server nur einen Android Custom-Scheme als Redirect-URI akzeptiert.

**Tech Stack:** Python 3.12+, aiohttp (HA-intern), pytest, aioresponses, pytest-homeassistant-custom-component

---

## Dateistruktur

```
custom_components/mybuderus/
├── __init__.py          # async_setup_entry / async_unload_entry
├── manifest.json        # HA Manifest
├── strings.json         # UI-Texte für Config Flow
├── const.py             # Konstanten + SensorEntityDescription-Tuple
├── auth.py              # OAuth2 PKCE: build_auth_url, exchange_code, refresh_access_token
├── api.py               # REST-Client: get_gateways, get_bulk, _extract_value
├── coordinator.py       # MyBuderusCoordinator (DataUpdateCoordinator)
├── sensor.py            # MyBuderusSensor (CoordinatorEntity + SensorEntity)
└── config_flow.py       # MyBuderusConfigFlow + MyBuderusOptionsFlow

tests/
└── mybuderus/
    ├── __init__.py
    ├── conftest.py
    ├── test_auth.py
    ├── test_api.py
    ├── test_coordinator.py
    └── test_config_flow.py
```

---

## Task 1: Scaffold

**Files:**
- Create: `custom_components/mybuderus/__init__.py` (stub)
- Create: `custom_components/mybuderus/manifest.json`
- Create: `tests/mybuderus/__init__.py`
- Create: `tests/mybuderus/conftest.py`
- Create: `requirements_test.txt`

- [ ] **Step 1: Verzeichnisstruktur anlegen**

```bash
mkdir -p custom_components/mybuderus
mkdir -p tests/mybuderus
touch custom_components/mybuderus/__init__.py
touch tests/mybuderus/__init__.py
```

- [ ] **Step 2: manifest.json schreiben**

`custom_components/mybuderus/manifest.json`:
```json
{
  "domain": "mybuderus",
  "name": "myBuderus",
  "version": "0.1.0",
  "config_flow": true,
  "documentation": "",
  "requirements": [],
  "dependencies": [],
  "codeowners": [],
  "iot_class": "cloud_polling"
}
```

`requirements` ist leer — `aiohttp` ist in HA bereits enthalten.

- [ ] **Step 3: Test-Dependencies anlegen**

`requirements_test.txt`:
```
pytest>=7.4
pytest-asyncio>=0.23
aioresponses>=0.7.6
pytest-homeassistant-custom-component>=0.13
```

- [ ] **Step 4: conftest.py schreiben**

`tests/mybuderus/conftest.py`:
```python
"""Shared test fixtures for myBuderus."""
pytest_plugins = "pytest_homeassistant_custom_component"
```

- [ ] **Step 5: Test-Dependencies installieren**

```bash
pip install -r requirements_test.txt
```

Expected: Alle Pakete installieren ohne Fehler.

- [ ] **Step 6: __init__.py stub schreiben**

`custom_components/mybuderus/__init__.py`:
```python
"""myBuderus Home Assistant Integration."""
```

- [ ] **Step 7: Commit**

```bash
git add custom_components/ tests/ requirements_test.txt
git commit -m "feat: scaffold mybuderus custom component structure"
```

---

## Task 2: const.py

**Files:**
- Create: `custom_components/mybuderus/const.py`

- [ ] **Step 1: Failing test schreiben**

`tests/mybuderus/test_const.py`:
```python
"""Tests for const.py."""
from custom_components.mybuderus.const import DOMAIN, SENSORS, MyBuderusSensorDescription


def test_domain():
    assert DOMAIN == "mybuderus"


def test_sensors_count():
    assert len(SENSORS) == 14


def test_all_sensors_have_resource_path():
    for s in SENSORS:
        assert s.resource_path.startswith("/"), f"{s.key} hat keinen absoluten Pfad"


def test_sensor_keys_unique():
    keys = [s.key for s in SENSORS]
    assert len(keys) == len(set(keys))
```

- [ ] **Step 2: Test laufen lassen (muss fehlschlagen)**

```bash
pytest tests/mybuderus/test_const.py -v
```

Expected: FAIL mit `ModuleNotFoundError`

- [ ] **Step 3: const.py implementieren**

`custom_components/mybuderus/const.py`:
```python
"""Constants for myBuderus integration."""
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature

DOMAIN = "mybuderus"

# OAuth2 / SingleKey ID
CLIENT_ID = "762162C0-FA2D-4540-AE66-6489F189FADC"
AUTHORIZATION_ENDPOINT = "https://singlekey-id.com/auth/connect/authorize"
TOKEN_ENDPOINT = "https://singlekey-id.com/auth/connect/token"
REDIRECT_URI = "com.buderus.tt.dashtt://app/login"
SCOPES = (
    "openid email profile offline_access "
    "pointt.gateway.list pointt.gateway.resource.dashapp "
    "pointt.castt.flow.token-exchange bacon hcc.tariff.read"
)

# REST API
BASE_URL = "https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/"

# Config / Options
DEFAULT_SCAN_INTERVAL = 300  # seconds
MIN_SCAN_INTERVAL = 30
CONF_SCAN_INTERVAL = "scan_interval"


@dataclass(frozen=True, kw_only=True)
class MyBuderusSensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with the API resource path."""

    resource_path: str = ""


SENSORS: tuple[MyBuderusSensorDescription, ...] = (
    MyBuderusSensorDescription(
        key="hc_operation_mode",
        name="Heizkreis Betriebsart",
        resource_path="/heatingCircuits/hc1/operationMode",
        device_class=SensorDeviceClass.ENUM,
    ),
    MyBuderusSensorDescription(
        key="hc_room_setpoint",
        name="Heizkreis Solltemperatur",
        resource_path="/heatingCircuits/hc1/currentRoomSetpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="hc_room_temperature",
        name="Heizkreis Raumtemperatur",
        resource_path="/heatingCircuits/hc1/roomtemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="dhw_operation_mode",
        name="WW Betriebsart",
        resource_path="/dhwCircuits/dhw1/operationMode",
        device_class=SensorDeviceClass.ENUM,
    ),
    MyBuderusSensorDescription(
        key="dhw_actual_temp",
        name="WW Speichertemperatur",
        resource_path="/dhwCircuits/dhw1/actualTemp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="dhw_current_setpoint",
        name="WW Aktiver Sollwert",
        resource_path="/dhwCircuits/dhw1/currentSetpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="dhw_setpoint_high",
        name="WW Sollwert high",
        resource_path="/dhwCircuits/dhw1/temperatureLevels/high",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="dhw_setpoint_low",
        name="WW Sollwert low",
        resource_path="/dhwCircuits/dhw1/temperatureLevels/low",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="outdoor_temperature",
        name="Außentemperatur",
        resource_path="/system/sensors/temperatures/outdoor_t1",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="compressor_status",
        name="Kompressorstatus",
        resource_path="/heatSources/compressor/status",
        device_class=SensorDeviceClass.ENUM,
    ),
    MyBuderusSensorDescription(
        key="supply_temperature",
        name="Vorlauftemperatur",
        resource_path="/heatSources/actualSupplyTemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="return_temperature",
        name="Rücklauftemperatur",
        resource_path="/heatSources/returnTemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MyBuderusSensorDescription(
        key="backup_heater_status",
        name="Zuheizerstatus",
        resource_path="/heatSources/Source/eHeater/status",
        device_class=SensorDeviceClass.ENUM,
    ),
    MyBuderusSensorDescription(
        key="system_mode",
        name="Systemmodus",
        resource_path="/system/seasonOptimizer/mode",
        device_class=SensorDeviceClass.ENUM,
    ),
)
```

- [ ] **Step 4: Tests laufen lassen**

```bash
pytest tests/mybuderus/test_const.py -v
```

Expected: 4 Tests PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/mybuderus/const.py tests/mybuderus/test_const.py
git commit -m "feat: add const.py with sensor descriptions"
```

---

## Task 3: auth.py

**Files:**
- Create: `custom_components/mybuderus/auth.py`
- Create: `tests/mybuderus/test_auth.py`

- [ ] **Step 1: Failing tests schreiben**

`tests/mybuderus/test_auth.py`:
```python
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
```

- [ ] **Step 2: Tests laufen lassen (müssen fehlschlagen)**

```bash
pytest tests/mybuderus/test_auth.py -v
```

Expected: FAIL mit `ModuleNotFoundError`

- [ ] **Step 3: auth.py implementieren**

`custom_components/mybuderus/auth.py`:
```python
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
```

- [ ] **Step 4: Tests laufen lassen**

```bash
pytest tests/mybuderus/test_auth.py -v
```

Expected: 10 Tests PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/mybuderus/auth.py tests/mybuderus/test_auth.py
git commit -m "feat: add auth.py with OAuth2 PKCE implementation"
```

---

## Task 4: api.py

**Files:**
- Create: `custom_components/mybuderus/api.py`
- Create: `tests/mybuderus/test_api.py`

- [ ] **Step 1: Failing tests schreiben**

`tests/mybuderus/test_api.py`:
```python
"""Tests for api.py."""
import pytest
import aiohttp
from aioresponses import aioresponses

from custom_components.mybuderus.api import _extract_value, get_bulk, get_gateways
from custom_components.mybuderus.const import BASE_URL

GATEWAYS_URL = BASE_URL + "gateways/"
BULK_URL = BASE_URL + "bulk"


# --- _extract_value ---

def test_extract_value_string():
    payload = {"type": "stringValue", "value": "manual"}
    assert _extract_value(payload) == "manual"


def test_extract_value_float():
    payload = {
        "type": "floatValue",
        "value": 7.5,
        "state": [{"short": 32767.0}, {"open": -32768.0}],
    }
    assert _extract_value(payload) == 7.5


def test_extract_value_sentinel_open():
    payload = {
        "type": "floatValue",
        "value": -32768.0,
        "state": [{"short": 32767.0}, {"open": -32768.0}],
    }
    assert _extract_value(payload) is None


def test_extract_value_sentinel_short():
    payload = {
        "type": "floatValue",
        "value": 32767.0,
        "state": [{"short": 32767.0}, {"open": -32768.0}],
    }
    assert _extract_value(payload) is None


def test_extract_value_none_payload():
    assert _extract_value(None) is None


# --- get_gateways ---

@pytest.mark.asyncio
async def test_get_gateways_returns_list():
    with aioresponses() as mock:
        mock.get(
            GATEWAYS_URL,
            payload=[{"deviceId": "101739215", "deviceType": "MX300"}],
        )
        async with aiohttp.ClientSession() as session:
            result = await get_gateways(session, "fake_token")

    assert result == [{"deviceId": "101739215", "deviceType": "MX300"}]


@pytest.mark.asyncio
async def test_get_gateways_raises_on_401():
    with aioresponses() as mock:
        mock.get(GATEWAYS_URL, status=401)
        async with aiohttp.ClientSession() as session:
            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await get_gateways(session, "bad_token")
    assert exc_info.value.status == 401


# --- get_bulk ---

BULK_RESPONSE = [
    {
        "gatewayId": "101739215",
        "resourcePaths": [
            {
                "resourcePath": "/heatingCircuits/hc1/operationMode",
                "serverStatus": 200,
                "gatewayResponse": {
                    "status": 200,
                    "payload": {"type": "stringValue", "value": "manual"},
                },
            },
            {
                "resourcePath": "/heatSources/returnTemperature",
                "serverStatus": 200,
                "gatewayResponse": {
                    "status": 200,
                    "payload": {
                        "type": "floatValue",
                        "value": 45.4,
                        "state": [{"short": 32767.0}, {"open": -32768.0}],
                    },
                },
            },
            {
                "resourcePath": "/heatingCircuits/hc1/roomtemperature",
                "serverStatus": 200,
                "gatewayResponse": {
                    "status": 200,
                    "payload": {
                        "type": "floatValue",
                        "value": -32768.0,
                        "state": [{"short": 32767.0}, {"open": -32768.0}],
                    },
                },
            },
            {
                "resourcePath": "/system/seasonOptimizer/mode",
                "serverStatus": 200,
                "gatewayResponse": {"status": 200, "payload": None},
            },
            {
                "resourcePath": "/dhwCircuits/dhw1/actualStorageTemperature",
                "serverStatus": 403,
                "gatewayResponse": None,
            },
        ],
    }
]


@pytest.mark.asyncio
async def test_get_bulk_extracts_string_value():
    with aioresponses() as mock:
        mock.post(BULK_URL, payload=BULK_RESPONSE)
        async with aiohttp.ClientSession() as session:
            result = await get_bulk(session, "token", "101739215")

    assert result["/heatingCircuits/hc1/operationMode"] == "manual"


@pytest.mark.asyncio
async def test_get_bulk_extracts_float_value():
    with aioresponses() as mock:
        mock.post(BULK_URL, payload=BULK_RESPONSE)
        async with aiohttp.ClientSession() as session:
            result = await get_bulk(session, "token", "101739215")

    assert result["/heatSources/returnTemperature"] == 45.4


@pytest.mark.asyncio
async def test_get_bulk_sentinel_becomes_none():
    with aioresponses() as mock:
        mock.post(BULK_URL, payload=BULK_RESPONSE)
        async with aiohttp.ClientSession() as session:
            result = await get_bulk(session, "token", "101739215")

    assert result["/heatingCircuits/hc1/roomtemperature"] is None


@pytest.mark.asyncio
async def test_get_bulk_null_payload_becomes_none():
    with aioresponses() as mock:
        mock.post(BULK_URL, payload=BULK_RESPONSE)
        async with aiohttp.ClientSession() as session:
            result = await get_bulk(session, "token", "101739215")

    assert result["/system/seasonOptimizer/mode"] is None


@pytest.mark.asyncio
async def test_get_bulk_403_path_becomes_none():
    with aioresponses() as mock:
        mock.post(BULK_URL, payload=BULK_RESPONSE)
        async with aiohttp.ClientSession() as session:
            result = await get_bulk(session, "token", "101739215")

    assert result["/dhwCircuits/dhw1/actualStorageTemperature"] is None
```

- [ ] **Step 2: Tests laufen lassen (müssen fehlschlagen)**

```bash
pytest tests/mybuderus/test_api.py -v
```

Expected: FAIL mit `ModuleNotFoundError`

- [ ] **Step 3: api.py implementieren**

`custom_components/mybuderus/api.py`:
```python
"""myBuderus Pointt REST API client."""
from typing import Any

import aiohttp

from .const import BASE_URL

RESOURCE_PATHS: list[str] = [
    "/heatingCircuits/hc1/operationMode",
    "/heatingCircuits/hc1/currentRoomSetpoint",
    "/heatingCircuits/hc1/roomtemperature",
    "/dhwCircuits/dhw1/operationMode",
    "/dhwCircuits/dhw1/actualTemp",
    "/dhwCircuits/dhw1/currentSetpoint",
    "/dhwCircuits/dhw1/temperatureLevels/high",
    "/dhwCircuits/dhw1/temperatureLevels/low",
    "/system/sensors/temperatures/outdoor_t1",
    "/heatSources/compressor/status",
    "/heatSources/actualSupplyTemperature",
    "/heatSources/returnTemperature",
    "/heatSources/Source/eHeater/status",
    "/system/seasonOptimizer/mode",
]


def _extract_value(payload: dict | None) -> Any:
    """Extract value from API payload dict.

    Handles sentinel values from the 'state' array:
      -32768.0 (open circuit) and 32767.0 (short circuit) → None.
    """
    if payload is None:
        return None
    if not isinstance(payload, dict):
        return payload
    for key in ("value", "currentValue"):
        if key in payload:
            val = payload[key]
            sentinels = {v for s in payload.get("state", []) for v in s.values()}
            if val in sentinels:
                return None
            return val
    return None


async def get_gateways(
    session: aiohttp.ClientSession, access_token: str
) -> list[dict]:
    """Return list of gateways for this account. Each item has 'deviceId'."""
    async with session.get(
        BASE_URL + "gateways/",
        headers={"Authorization": f"Bearer {access_token}"},
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()
        return data if isinstance(data, list) else []


async def get_bulk(
    session: aiohttp.ClientSession,
    access_token: str,
    gateway_id: str,
) -> dict[str, Any]:
    """Fetch all resource paths via single bulk POST request.

    Returns dict mapping resource path → extracted value (None if unavailable).
    """
    body = [{"gatewayId": gateway_id, "resourcePaths": RESOURCE_PATHS}]
    async with session.post(
        BASE_URL + "bulk",
        headers={"Authorization": f"Bearer {access_token}"},
        json=body,
    ) as resp:
        resp.raise_for_status()
        raw = await resp.json()

    result: dict[str, Any] = {}
    for gateway_resp in raw:
        for rp in gateway_resp.get("resourcePaths", []):
            path = rp.get("resourcePath", "")
            server_status = rp.get("serverStatus", 200)
            gateway_response = rp.get("gatewayResponse") or {}
            payload = gateway_response.get("payload")
            result[path] = None if server_status >= 400 else _extract_value(payload)
    return result
```

- [ ] **Step 4: Tests laufen lassen**

```bash
pytest tests/mybuderus/test_api.py -v
```

Expected: 11 Tests PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/mybuderus/api.py tests/mybuderus/test_api.py
git commit -m "feat: add api.py with bulk request and value extraction"
```

---

## Task 5: coordinator.py

**Files:**
- Create: `custom_components/mybuderus/coordinator.py`
- Create: `tests/mybuderus/test_coordinator.py`

- [ ] **Step 1: Failing tests schreiben**

`tests/mybuderus/test_coordinator.py`:
```python
"""Tests for coordinator.py."""
import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.mybuderus.coordinator import MyBuderusCoordinator

ENTRY_DATA = {
    "access_token": "acc_token",
    "refresh_token": "ref_token",
    "expires_at": time.time() + 3600,
    "gateway_id": "101739215",
}

BULK_DATA = {"/heatingCircuits/hc1/operationMode": "manual"}


@pytest.fixture
def mock_entry(hass):
    entry = MagicMock()
    entry.data = dict(ENTRY_DATA)
    entry.entry_id = "test_entry"
    return entry


@pytest.fixture
def coordinator(hass, mock_entry):
    session = MagicMock(spec=aiohttp.ClientSession)
    return MyBuderusCoordinator(
        hass=hass,
        session=session,
        entry=mock_entry,
        scan_interval=300,
    )


@pytest.mark.asyncio
async def test_update_returns_bulk_data(hass, coordinator):
    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(return_value=BULK_DATA),
    ):
        result = await coordinator._async_update_data()

    assert result == BULK_DATA


@pytest.mark.asyncio
async def test_update_refreshes_expired_token(hass, coordinator):
    coordinator._expires_at = time.time() - 10  # expired

    new_token = {
        "access_token": "new_acc",
        "refresh_token": "new_ref",
        "expires_in": 3600,
    }

    with patch(
        "custom_components.mybuderus.coordinator.refresh_access_token",
        new=AsyncMock(return_value=new_token),
    ), patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(return_value=BULK_DATA),
    ):
        await coordinator._async_update_data()

    assert coordinator._access_token == "new_acc"
    assert coordinator._refresh_token == "new_ref"


@pytest.mark.asyncio
async def test_update_raises_auth_failed_on_refresh_401(hass, coordinator):
    coordinator._expires_at = time.time() - 10

    error = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=401)
    with patch(
        "custom_components.mybuderus.coordinator.refresh_access_token",
        new=AsyncMock(side_effect=error),
    ):
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_update_raises_update_failed_on_network_error(hass, coordinator):
    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(side_effect=aiohttp.ClientError("timeout")),
    ):
        with pytest.raises(UpdateFailed, match="Network error"):
            await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_update_retries_after_401_on_bulk(hass, coordinator):
    """On 401 from bulk, coordinator should refresh token and retry."""
    bulk_401 = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=401)
    new_token = {"access_token": "new_acc", "refresh_token": "new_ref", "expires_in": 3600}

    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(side_effect=[bulk_401, BULK_DATA]),
    ), patch(
        "custom_components.mybuderus.coordinator.refresh_access_token",
        new=AsyncMock(return_value=new_token),
    ):
        result = await coordinator._async_update_data()

    assert result == BULK_DATA


def test_gateway_id_property(coordinator):
    assert coordinator.gateway_id == "101739215"
```

- [ ] **Step 2: Tests laufen lassen (müssen fehlschlagen)**

```bash
pytest tests/mybuderus/test_coordinator.py -v
```

Expected: FAIL mit `ModuleNotFoundError`

- [ ] **Step 3: coordinator.py implementieren**

`custom_components/mybuderus/coordinator.py`:
```python
"""DataUpdateCoordinator for myBuderus."""
import logging
import time
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import get_bulk
from .auth import refresh_access_token
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MyBuderusCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manages polling of all myBuderus data points."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        entry: ConfigEntry,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._session = session
        self._entry = entry
        self._access_token: str = entry.data["access_token"]
        self._refresh_token: str = entry.data["refresh_token"]
        self._expires_at: float = entry.data["expires_at"]
        self._gateway_id: str = entry.data["gateway_id"]

    @property
    def gateway_id(self) -> str:
        """Return the gateway device ID."""
        return self._gateway_id

    async def _do_token_refresh(self) -> None:
        """Refresh the access token and persist new tokens to config entry."""
        try:
            token_data = await refresh_access_token(self._session, self._refresh_token)
        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                raise ConfigEntryAuthFailed("Refresh token expired") from err
            raise UpdateFailed(f"Token refresh failed: {err}") from err

        self._access_token = token_data["access_token"]
        self._refresh_token = token_data.get("refresh_token", self._refresh_token)
        self._expires_at = time.time() + token_data.get("expires_in", 3600)

        self.hass.config_entries.async_update_entry(
            self._entry,
            data={
                **self._entry.data,
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
                "expires_at": self._expires_at,
            },
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Pointt API."""
        if time.time() > self._expires_at - 60:
            await self._do_token_refresh()

        try:
            return await get_bulk(self._session, self._access_token, self._gateway_id)
        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                await self._do_token_refresh()
                try:
                    return await get_bulk(
                        self._session, self._access_token, self._gateway_id
                    )
                except aiohttp.ClientResponseError as retry_err:
                    raise ConfigEntryAuthFailed("Authentication failed") from retry_err
            raise UpdateFailed(f"API error: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Network error: {err}") from err
```

- [ ] **Step 4: Tests laufen lassen**

```bash
pytest tests/mybuderus/test_coordinator.py -v
```

Expected: 6 Tests PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/mybuderus/coordinator.py tests/mybuderus/test_coordinator.py
git commit -m "feat: add DataUpdateCoordinator with token refresh and retry logic"
```

---

## Task 6: sensor.py + __init__.py

**Files:**
- Create: `custom_components/mybuderus/sensor.py`
- Modify: `custom_components/mybuderus/__init__.py`
- Create: `tests/mybuderus/test_sensor.py`

- [ ] **Step 1: Failing tests schreiben**

`tests/mybuderus/test_sensor.py`:
```python
"""Tests for sensor.py."""
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import STATE_UNAVAILABLE

from custom_components.mybuderus.const import DOMAIN, SENSORS


@pytest.fixture
def entry(hass):
    from homeassistant.config_entries import ConfigEntry
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.title = "myBuderus Test"
    entry.data = {
        "access_token": "acc",
        "refresh_token": "ref",
        "expires_at": time.time() + 3600,
        "gateway_id": "101739215",
    }
    entry.options = {"scan_interval": 300}
    return entry


@pytest.fixture
def coordinator(hass, entry):
    from unittest.mock import MagicMock
    import aiohttp
    from custom_components.mybuderus.coordinator import MyBuderusCoordinator

    session = MagicMock(spec=aiohttp.ClientSession)
    coord = MyBuderusCoordinator(hass, session, entry, 300)
    coord.data = {
        "/heatingCircuits/hc1/operationMode": "manual",
        "/heatSources/returnTemperature": 45.4,
        "/heatingCircuits/hc1/roomtemperature": None,
        "/system/seasonOptimizer/mode": None,
    }
    return coord


@pytest.mark.asyncio
async def test_sensors_created_for_all_descriptions(hass, coordinator, entry):
    from custom_components.mybuderus.sensor import MyBuderusSensor

    entities = [MyBuderusSensor(coordinator, desc, entry) for desc in SENSORS]
    assert len(entities) == 14


@pytest.mark.asyncio
async def test_sensor_native_value_string(hass, coordinator, entry):
    from custom_components.mybuderus.sensor import MyBuderusSensor
    from custom_components.mybuderus.const import SENSORS

    desc = next(s for s in SENSORS if s.key == "hc_operation_mode")
    sensor = MyBuderusSensor(coordinator, desc, entry)
    assert sensor.native_value == "manual"


@pytest.mark.asyncio
async def test_sensor_native_value_float(hass, coordinator, entry):
    from custom_components.mybuderus.sensor import MyBuderusSensor
    from custom_components.mybuderus.const import SENSORS

    desc = next(s for s in SENSORS if s.key == "return_temperature")
    sensor = MyBuderusSensor(coordinator, desc, entry)
    assert sensor.native_value == 45.4


@pytest.mark.asyncio
async def test_sensor_native_value_none_for_unavailable(hass, coordinator, entry):
    from custom_components.mybuderus.sensor import MyBuderusSensor
    from custom_components.mybuderus.const import SENSORS

    desc = next(s for s in SENSORS if s.key == "hc_room_temperature")
    sensor = MyBuderusSensor(coordinator, desc, entry)
    assert sensor.native_value is None


@pytest.mark.asyncio
async def test_sensor_unique_id_format(hass, coordinator, entry):
    from custom_components.mybuderus.sensor import MyBuderusSensor
    from custom_components.mybuderus.const import SENSORS

    desc = SENSORS[0]
    sensor = MyBuderusSensor(coordinator, desc, entry)
    assert sensor.unique_id == f"test_entry_{desc.key}"
```

- [ ] **Step 2: Tests laufen lassen (müssen fehlschlagen)**

```bash
pytest tests/mybuderus/test_sensor.py -v
```

Expected: FAIL mit `ModuleNotFoundError`

- [ ] **Step 3: sensor.py implementieren**

`custom_components/mybuderus/sensor.py`:
```python
"""Sensor entities for myBuderus."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSORS, MyBuderusSensorDescription
from .coordinator import MyBuderusCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up myBuderus sensor entities from config entry."""
    coordinator: MyBuderusCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MyBuderusSensor(coordinator, description, entry)
        for description in SENSORS
    )


class MyBuderusSensor(CoordinatorEntity[MyBuderusCoordinator], SensorEntity):
    """A single myBuderus sensor entity backed by the coordinator."""

    entity_description: MyBuderusSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MyBuderusCoordinator,
        description: MyBuderusSensorDescription,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.gateway_id)},
            name=entry.title,
            manufacturer="Bosch",
            model="myBuderus",
        )

    @property
    def native_value(self):
        """Return the current sensor value from coordinator data."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.resource_path)
```

- [ ] **Step 4: __init__.py implementieren**

`custom_components/mybuderus/__init__.py`:
```python
"""myBuderus Home Assistant Integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import MyBuderusCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up myBuderus from config entry."""
    session = async_get_clientsession(hass)
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = MyBuderusCoordinator(
        hass=hass,
        session=session,
        entry=entry,
        scan_interval=scan_interval,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload myBuderus config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
```

- [ ] **Step 5: Tests laufen lassen**

```bash
pytest tests/mybuderus/test_sensor.py -v
```

Expected: 5 Tests PASS

- [ ] **Step 6: Commit**

```bash
git add custom_components/mybuderus/sensor.py custom_components/mybuderus/__init__.py tests/mybuderus/test_sensor.py
git commit -m "feat: add sensor entities and integration setup"
```

---

## Task 7: config_flow.py + strings.json

**Files:**
- Create: `custom_components/mybuderus/config_flow.py`
- Create: `custom_components/mybuderus/strings.json`
- Create: `tests/mybuderus/test_config_flow.py`

- [ ] **Step 1: Failing tests schreiben**

`tests/mybuderus/test_config_flow.py`:
```python
"""Tests for config_flow.py."""
import time
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.mybuderus.const import DOMAIN

TOKEN_DATA = {
    "access_token": "acc_token",
    "refresh_token": "ref_token",
    "expires_in": 3600,
}
GATEWAYS = [{"deviceId": "101739215"}]


@pytest.mark.asyncio
async def test_flow_user_step_shows_form(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    # Auth URL must be in description_placeholders
    assert "auth_url" in result["description_placeholders"]


@pytest.mark.asyncio
async def test_flow_user_step_invalid_code_shows_error(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.mybuderus.config_flow.exchange_code",
        new=AsyncMock(side_effect=aiohttp.ClientResponseError(None, None, status=400)),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"auth_code": "bad_code"}
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert "cannot_connect" in result2["errors"].get("base", "") or \
           "cannot_connect" in result2["errors"].get("auth_code", "")


@pytest.mark.asyncio
async def test_flow_creates_entry_with_valid_code(hass):
    init_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.mybuderus.config_flow.exchange_code",
        new=AsyncMock(return_value=TOKEN_DATA),
    ), patch(
        "custom_components.mybuderus.config_flow.get_gateways",
        new=AsyncMock(return_value=GATEWAYS),
    ):
        step2 = await hass.config_entries.flow.async_configure(
            init_result["flow_id"],
            user_input={"auth_code": "valid_code"},
        )

    assert step2["type"] == FlowResultType.FORM
    assert step2["step_id"] == "config"

    result = await hass.config_entries.flow.async_configure(
        init_result["flow_id"],
        user_input={"name": "Test WP", "scan_interval": 120},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test WP"
    assert result["data"]["gateway_id"] == "101739215"
    assert result["data"]["access_token"] == "acc_token"
    assert result["options"]["scan_interval"] == 120


@pytest.mark.asyncio
async def test_options_flow_updates_scan_interval(hass):
    # Create entry first
    entry = hass.config_entries.async_entries(DOMAIN)
    # We need an existing entry — create it manually for the options flow test
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock

    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_opt"
    mock_entry.options = {"scan_interval": 300}
    mock_entry.domain = DOMAIN

    from custom_components.mybuderus.config_flow import MyBuderusOptionsFlow
    flow = MyBuderusOptionsFlow(mock_entry)
    flow.hass = hass

    result = await flow.async_step_init(None)
    assert result["type"] == FlowResultType.FORM

    result2 = await flow.async_step_init({"scan_interval": 60})
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["scan_interval"] == 60
```

- [ ] **Step 2: Tests laufen lassen (müssen fehlschlagen)**

```bash
pytest tests/mybuderus/test_config_flow.py -v
```

Expected: FAIL mit `ModuleNotFoundError`

- [ ] **Step 3: config_flow.py implementieren**

`custom_components/mybuderus/config_flow.py`:
```python
"""Config flow for myBuderus."""
import time
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import get_gateways
from .auth import build_auth_url, exchange_code, extract_code, generate_pkce_pair
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, MIN_SCAN_INTERVAL


class MyBuderusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for myBuderus."""

    VERSION = 1

    def __init__(self) -> None:
        self._code_verifier: str = ""
        self._auth_url: str = ""
        self._token_data: dict = {}
        self._gateway_id: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Show auth URL and code input field."""
        if not self._auth_url:
            code_verifier, code_challenge = generate_pkce_pair()
            self._code_verifier = code_verifier
            self._auth_url = build_auth_url(code_challenge)

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                code = extract_code(user_input["auth_code"])
            except ValueError:
                errors["auth_code"] = "invalid_code"
            else:
                session = async_get_clientsession(self.hass)
                try:
                    self._token_data = await exchange_code(
                        session, code, self._code_verifier
                    )
                    gateways = await get_gateways(
                        session, self._token_data["access_token"]
                    )
                    self._gateway_id = gateways[0]["deviceId"]
                except (aiohttp.ClientResponseError, IndexError, KeyError):
                    errors["base"] = "cannot_connect"
                else:
                    return await self.async_step_config()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("auth_code"): str}),
            description_placeholders={"auth_url": self._auth_url},
            errors=errors,
        )

    async def async_step_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: Name and polling interval."""
        if user_input is not None:
            entry_data = {
                "access_token": self._token_data["access_token"],
                "refresh_token": self._token_data["refresh_token"],
                "expires_at": time.time() + self._token_data.get("expires_in", 3600),
                "gateway_id": self._gateway_id,
            }
            return self.async_create_entry(
                title=user_input["name"],
                data=entry_data,
                options={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]},
            )

        return self.async_show_form(
            step_id="config",
            data_schema=vol.Schema({
                vol.Required("name", default="myBuderus"): str,
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    int, vol.Range(min=MIN_SCAN_INTERVAL)
                ),
            }),
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when token refresh fails."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show re-auth form with new login link."""
        if not self._auth_url:
            code_verifier, code_challenge = generate_pkce_pair()
            self._code_verifier = code_verifier
            self._auth_url = build_auth_url(code_challenge)

        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            try:
                code = extract_code(user_input["auth_code"])
                token_data = await exchange_code(session, code, self._code_verifier)
            except (ValueError, aiohttp.ClientResponseError):
                errors["auth_code"] = "invalid_code"
            else:
                entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        "access_token": token_data["access_token"],
                        "refresh_token": token_data["refresh_token"],
                        "expires_at": time.time() + token_data.get("expires_in", 3600),
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required("auth_code"): str}),
            description_placeholders={"auth_url": self._auth_url},
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> "MyBuderusOptionsFlow":
        return MyBuderusOptionsFlow(config_entry)


class MyBuderusOptionsFlow(OptionsFlow):
    """Options flow for adjusting the polling interval."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self._config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    int, vol.Range(min=MIN_SCAN_INTERVAL)
                ),
            }),
        )
```

- [ ] **Step 4: strings.json schreiben**

`custom_components/mybuderus/strings.json`:
```json
{
  "config": {
    "step": {
      "user": {
        "title": "myBuderus Anmeldung",
        "description": "**Schritt-für-Schritt:**\n\n1. Öffne diesen Link im Browser: [{auth_url}]({auth_url})\n2. Melde dich mit deinen SingleKey ID Zugangsdaten an\n3. Nach dem Login erscheint eine Fehlerseite — das ist normal\n4. Öffne die Entwicklerkonsole (F12) → Netzwerk-Tab\n5. Filtere nach `com.buderus` und kopiere die vollständige URL\n6. Füge die URL oder nur den `code`-Parameter unten ein",
        "data": {
          "auth_code": "Redirect-URL oder Code"
        }
      },
      "config": {
        "title": "Konfiguration",
        "data": {
          "name": "Name der Integration",
          "scan_interval": "Aktualisierungsintervall (Sekunden)"
        }
      },
      "reauth_confirm": {
        "title": "myBuderus — Erneut anmelden",
        "description": "Die Anmeldedaten sind abgelaufen.\n\n1. Öffne diesen Link: [{auth_url}]({auth_url})\n2. Melde dich an\n3. Kopiere die Redirect-URL aus den DevTools (Netzwerk-Tab → `com.buderus`)",
        "data": {
          "auth_code": "Redirect-URL oder Code"
        }
      }
    },
    "error": {
      "invalid_code": "Ungültiger Code oder URL.",
      "cannot_connect": "Verbindung fehlgeschlagen. Bitte Internetverbindung prüfen."
    },
    "abort": {
      "reauth_successful": "Anmeldung erfolgreich erneuert."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "myBuderus Einstellungen",
        "data": {
          "scan_interval": "Aktualisierungsintervall (Sekunden)"
        }
      }
    }
  }
}
```

- [ ] **Step 5: Tests laufen lassen**

```bash
pytest tests/mybuderus/test_config_flow.py -v
```

Expected: 4 Tests PASS

- [ ] **Step 6: Alle Tests laufen lassen**

```bash
pytest tests/mybuderus/ -v
```

Expected: Alle Tests PASS, kein FAIL

- [ ] **Step 7: Commit**

```bash
git add custom_components/mybuderus/config_flow.py custom_components/mybuderus/strings.json tests/mybuderus/test_config_flow.py
git commit -m "feat: add config flow with OAuth2 copy-paste auth and options flow"
```

---

## Task 8: Manuelle Installation & Smoke Test

**Files:** keine neuen Dateien — Installation und Test in HA

Dieser Task validiert die komplette Integration in einer echten HA-Instanz.

- [ ] **Step 1: custom_components-Ordner in HA kopieren**

```bash
# Pfad zu deiner HA-Konfiguration anpassen:
cp -r custom_components/mybuderus ~/.homeassistant/custom_components/
```

- [ ] **Step 2: HA neu starten**

HA-Instanz neu starten (Einstellungen → System → Neustart).

- [ ] **Step 3: Integration hinzufügen**

HA → Einstellungen → Geräte & Dienste → Integration hinzufügen → "myBuderus" suchen → Auswählen.

- [ ] **Step 4: Config Flow durchlaufen**

- Auth-Link aus Step 1 des Config Flows öffnen
- Mit SingleKey ID einloggen
- DevTools öffnen (F12) → Netzwerk-Tab → `com.buderus` filtern → URL kopieren
- URL in das Textfeld einfügen → Weiter
- Name und Intervall bestätigen → Fertig

- [ ] **Step 5: Sensoren prüfen**

HA → Einstellungen → Geräte & Dienste → myBuderus → Entitäten.

Expected: 14 Sensoren sichtbar. Temperatursensoren zeigen Werte in °C. String-Sensoren zeigen Betriebsart. Sensoren ohne Wert (Raumtemperatur, Systemmodus) zeigen `unavailable`.

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: myBuderus HA custom component Phase 3 complete" --allow-empty
```

---

## Self-Review

**Spec-Abdeckung:**
- ✓ Alle 14 Sensor-Entities mit resource_path, device_class, unit
- ✓ Konfigurierbares Polling-Intervall (default 300s, min 30s) in Options Flow
- ✓ Step-by-step Config Flow mit DevTools-Anleitung und Textfeld
- ✓ Sentinel-Werte → None → HA `unavailable`
- ✓ Token-Refresh automatisch im Coordinator
- ✓ Re-Auth Flow bei abgelaufenem Refresh Token
- ✓ 403 per Pfad → betroffener Sensor `unavailable`, andere weiter verfügbar
- ✓ Tests für auth, api, coordinator, config_flow, sensor
- ✓ `aiohttp` (HA-intern, kein extra Dependency)
- ✓ Kein Code-Sharing mit Prototyp

**Typ-Konsistenz:**
- `get_bulk` gibt `dict[str, Any]` zurück — Coordinator speichert es als `self.data` — Sensor liest `self.coordinator.data.get(resource_path)`
- `MyBuderusCoordinator` nimmt `entry: ConfigEntry` — `__init__.py` übergibt `entry` direkt
- `gateway_id` ist Public Property am Coordinator — `sensor.py` liest `coordinator.gateway_id`
