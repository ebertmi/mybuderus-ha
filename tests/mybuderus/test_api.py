"""Tests for api.py."""
import pytest
import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
async def test_get_gateways_returns_list(hass, aioclient_mock):
    aioclient_mock.get(
        GATEWAYS_URL,
        json=[{"deviceId": "101739215", "deviceType": "MX300"}],
    )
    session = async_get_clientsession(hass)
    result = await get_gateways(session, "fake_token")

    assert result == [{"deviceId": "101739215", "deviceType": "MX300"}]


@pytest.mark.asyncio
async def test_get_gateways_raises_on_401(hass, aioclient_mock):
    aioclient_mock.get(GATEWAYS_URL, status=401)
    session = async_get_clientsession(hass)
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
async def test_get_bulk_extracts_string_value(hass, aioclient_mock):
    aioclient_mock.post(BULK_URL, json=BULK_RESPONSE)
    session = async_get_clientsession(hass)
    result = await get_bulk(session, "token", "101739215")

    assert result["/heatingCircuits/hc1/operationMode"] == "manual"


@pytest.mark.asyncio
async def test_get_bulk_extracts_float_value(hass, aioclient_mock):
    aioclient_mock.post(BULK_URL, json=BULK_RESPONSE)
    session = async_get_clientsession(hass)
    result = await get_bulk(session, "token", "101739215")

    assert result["/heatSources/returnTemperature"] == 45.4


@pytest.mark.asyncio
async def test_get_bulk_sentinel_becomes_none(hass, aioclient_mock):
    aioclient_mock.post(BULK_URL, json=BULK_RESPONSE)
    session = async_get_clientsession(hass)
    result = await get_bulk(session, "token", "101739215")

    assert result["/heatingCircuits/hc1/roomtemperature"] is None


@pytest.mark.asyncio
async def test_get_bulk_null_payload_becomes_none(hass, aioclient_mock):
    aioclient_mock.post(BULK_URL, json=BULK_RESPONSE)
    session = async_get_clientsession(hass)
    result = await get_bulk(session, "token", "101739215")

    assert result["/system/seasonOptimizer/mode"] is None


@pytest.mark.asyncio
async def test_get_bulk_403_path_becomes_none(hass, aioclient_mock):
    aioclient_mock.post(BULK_URL, json=BULK_RESPONSE)
    session = async_get_clientsession(hass)
    result = await get_bulk(session, "token", "101739215")

    assert result["/dhwCircuits/dhw1/actualStorageTemperature"] is None
