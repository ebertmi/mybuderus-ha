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
