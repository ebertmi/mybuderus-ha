"""Tests for coordinator.py."""
import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
import pytest_asyncio
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


@pytest_asyncio.fixture
async def mock_entry(hass):
    entry = MagicMock()
    entry.data = dict(ENTRY_DATA)
    entry.entry_id = "test_entry"
    return entry


@pytest_asyncio.fixture
async def coordinator(hass, mock_entry):
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
    ), patch.object(
        hass.config_entries, "async_update_entry"
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
    ), patch.object(
        hass.config_entries, "async_update_entry"
    ):
        result = await coordinator._async_update_data()

    assert result == BULK_DATA


@pytest.mark.asyncio
async def test_gateway_id_property(coordinator):
    assert coordinator.gateway_id == "101739215"
