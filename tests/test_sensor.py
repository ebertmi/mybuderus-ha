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
