"""
myBuderus Prototyp — authentifiziert und ruft alle Datenpunkte ab.

Verwendung:
  cd prototype
  source .venv/bin/activate
  python main.py
"""
from auth import get_access_token
from api import get_bulk, get_gateways

# Alle Endpunkte (Pfade relativ zu gateways/{deviceId}/resource/)
# Quelle: APK-Analyse (docs/api-spec.md)
RESOURCE_PATHS = [
    # Heizkreis
    "heatingCircuits/hc1/operationMode",
    "heatingCircuits/hc1/currentRoomSetpoint",
    "heatingCircuits/hc1/roomtemperature",
    # Warmwasser
    "dhwCircuits/dhw1/operationMode",
    "dhwCircuits/dhw1/currentTemperatureLevel",
    # Echtzeit-Daten (Wärmepumpe)
    "system/sensors/temperatures/outdoor_t1",
    "heatSources/compressor/status",
    "heatSources/actualSupplyTemperature",
    "heatSources/returnTemperature",
    "heatSources/Source/eHeater/status",
    "system/seasonOptimizer/mode",
    # System-Info
    "system/info",
    "heatSources/info",
]

LABELS = {
    "heatingCircuits/hc1/operationMode":          "Heizkreis Betriebsart",
    "heatingCircuits/hc1/currentRoomSetpoint":    "Heizkreis Solltemperatur",
    "heatingCircuits/hc1/roomtemperature":        "Heizkreis Raumtemperatur",
    "dhwCircuits/dhw1/operationMode":             "Warmwasser Betriebsart",
    "dhwCircuits/dhw1/currentTemperatureLevel":   "Warmwasser Ist-Temperatur",
    "system/sensors/temperatures/outdoor_t1":    "Außentemperatur",
    "heatSources/compressor/status":              "Kompressorstatus",
    "heatSources/actualSupplyTemperature":        "Vorlauftemperatur",
    "heatSources/returnTemperature":              "Rücklauftemperatur",
    "heatSources/Source/eHeater/status":          "Zuheizerstatus",
    "system/seasonOptimizer/mode":                "Systemmodus",
    "system/info":                                "System Info",
    "heatSources/info":                           "Wärmequellen Info",
}


def extract_value(payload) -> str:
    """Extract display value from API payload.

    floatValue endpoints use sentinel values to indicate sensor errors:
      -32768.0 = open circuit (sensor not connected)
       32767.0 = short circuit
    These are listed in payload['state'] and must be treated as unavailable.
    """
    if payload is None:
        return "N/A"
    if isinstance(payload, dict):
        for key in ("value", "currentValue", "body"):
            if key in payload:
                val = payload[key]
                # Check sentinel values from the 'state' list
                sentinels = {v for s in payload.get("state", []) for v in s.values()}
                if val in sentinels:
                    return "N/A"
                unit = payload.get("unitOfMeasure", "")
                return f"{val} {unit}".strip() if unit else str(val)
        return str(payload)
    return str(payload)


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
    gateway_id = gateway.get("deviceId") or gateway.get("gatewayId") or gateway.get("id")
    if not gateway_id:
        print(f"FEHLER: Kein Gateway-ID-Feld gefunden. Rohdaten: {gateway}")
        return
    print(f"   Gateway-ID: {gateway_id}")

    print("\n3. Datenpunkte abrufen (Bulk-Request)...")
    results = get_bulk(token, gateway_id, RESOURCE_PATHS)

    print("\n=== Ergebnisse ===")
    for item in results:
        path = item.get("path", "").lstrip("/")
        payload = item.get("payload")
        status = item.get("status")
        label = LABELS.get(path, path)

        if status and status >= 400:
            print(f"  ✗ {label}: HTTP {status}")
        else:
            value = extract_value(payload)
            print(f"  ✓ {label}: {value}")

    print("\n=== Rohdaten (für api-spec.md) ===")
    for item in results:
        print(f"  {item.get('path')}: {item.get('payload')}")


if __name__ == "__main__":
    main()
