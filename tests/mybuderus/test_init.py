"""Tests for __init__.py."""
import time
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mybuderus.const import CONF_SCAN_INTERVAL, DOMAIN

ENTRY_DATA = {
    "access_token": "acc_token",
    "refresh_token": "ref_token",
    "expires_at": time.time() + 3600,
    "gateway_id": "101739215",
}

BULK_DATA = {"/heatSources/compressor/status": "off"}


@pytest.fixture
async def setup_entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=dict(ENTRY_DATA),
        options={CONF_SCAN_INTERVAL: 300},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(return_value=BULK_DATA),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


@pytest.mark.asyncio
async def test_token_update_does_not_reload_entry(hass, setup_entry):
    """Persisting refreshed tokens must not reload the integration (issue #1)."""
    with patch.object(
        hass.config_entries, "async_reload", new=AsyncMock()
    ) as mock_reload:
        hass.config_entries.async_update_entry(
            setup_entry,
            data={**setup_entry.data, "access_token": "new_acc"},
        )
        await hass.async_block_till_done()

    mock_reload.assert_not_called()


@pytest.mark.asyncio
async def test_options_update_reloads_entry(hass, setup_entry):
    with patch.object(
        hass.config_entries, "async_reload", new=AsyncMock()
    ) as mock_reload:
        hass.config_entries.async_update_entry(
            setup_entry, options={CONF_SCAN_INTERVAL: 600}
        )
        await hass.async_block_till_done()

    mock_reload.assert_called_once_with(setup_entry.entry_id)
