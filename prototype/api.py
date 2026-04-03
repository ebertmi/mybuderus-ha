"""
myBuderus Pointt REST API Client.
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
    Returns list of gateways for this account.
    Each item has 'deviceId' (use this as gatewayId in all subsequent calls).
    """
    resp = httpx.get(
        BASE_URL + "gateways/",
        headers=_headers(access_token),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    # Defensive: handle unexpected wrapper
    for key in ("body", "gateways", "items"):
        if isinstance(data, dict) and key in data:
            return data[key]
    return [data]


def get_resource(access_token: str, gateway_id: str, path: str) -> Any:
    """
    GET a single resource endpoint.
    path: e.g. 'heatingCircuits/hc1/operationMode'
    """
    url = BASE_URL + f"gateways/{gateway_id}/resource/{path}"
    resp = httpx.get(url, headers=_headers(access_token), timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_bulk(access_token: str, gateway_id: str, paths: list[str]) -> list[dict]:
    """
    POST to bulk endpoint to fetch multiple resources in one request.

    Bulk endpoint: POST /bulk
    Body: [{"gatewayId": "...", "resourcePaths": ["/path1", "/path2"]}]
    Response: [{"gatewayId": "...", "resourcePaths": [{"resourcePath": "/path", "serverStatus": 200, "gatewayResponse": {"status": 200, "payload": {...}}}]}]

    Returns a flat list of dicts: [{"path": "/path", "payload": {...}, "status": 200}, ...]
    Falls back to individual GET requests if bulk fails.
    """
    body = [{"gatewayId": gateway_id, "resourcePaths": [f"/{p}" for p in paths]}]
    resp = httpx.post(
        BASE_URL + "bulk",
        headers=_headers(access_token),
        json=body,
        timeout=20,
    )

    if resp.status_code in (404, 405):
        print("  Bulk-Endpunkt nicht verfügbar, falle zurück auf Einzel-Requests...")
        return _get_individually(access_token, gateway_id, paths)

    resp.raise_for_status()
    raw = resp.json()

    # Flatten nested response structure
    results = []
    for gateway_resp in raw:
        for rp in gateway_resp.get("resourcePaths", []):
            gateway_response = rp.get("gatewayResponse") or {}
            results.append({
                "path": rp.get("resourcePath", ""),
                "status": rp.get("serverStatus"),
                "payload": gateway_response.get("payload"),
            })
    return results


def _get_individually(access_token: str, gateway_id: str, paths: list[str]) -> list[dict]:
    """Fallback: fetch each resource individually."""
    results = []
    for path in paths:
        try:
            data = get_resource(access_token, gateway_id, path)
            results.append({"path": f"/{path}", "status": 200, "payload": data})
        except httpx.HTTPStatusError as e:
            results.append({"path": f"/{path}", "status": e.response.status_code, "payload": None})
    return results
