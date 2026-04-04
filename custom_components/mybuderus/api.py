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
