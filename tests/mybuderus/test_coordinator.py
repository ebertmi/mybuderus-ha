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
async def test_update_raises_auth_failed_on_refresh_400(hass, coordinator):
    """400 Bad Request on token endpoint means refresh token is invalid/expired."""
    coordinator._expires_at = time.time() - 10

    error = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=400)
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


def test_initial_health_state(coordinator):
    """Coordinator starts with no recorded success and zero failures."""
    assert coordinator._last_success_at is None
    assert coordinator._consecutive_failures == 0
    assert coordinator._outage_issue_active is False


def test_format_last_success_never(coordinator):
    coordinator._last_success_at = None
    assert coordinator._format_last_success() == "never"


def test_format_last_success_minutes(coordinator):
    coordinator._last_success_at = time.time() - 90  # 1m 30s ago
    result = coordinator._format_last_success()
    assert "m ago" in result
    assert "1m ago" in result


def test_format_last_success_hours(coordinator):
    coordinator._last_success_at = time.time() - 7500  # 2h 5m ago
    result = coordinator._format_last_success()
    assert "h" in result and "m ago" in result


def test_format_last_success_days(coordinator):
    coordinator._last_success_at = time.time() - (4 * 86400 + 7200)  # 4d 2h ago
    result = coordinator._format_last_success()
    assert result.startswith("4d")


def test_classify_http_error_403(coordinator):
    err = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=403)
    assert "Permission denied" in coordinator._classify_http_error(err)


def test_classify_http_error_404(coordinator):
    err = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=404)
    assert "Endpoint not found" in coordinator._classify_http_error(err)


def test_classify_http_error_429(coordinator):
    err = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=429)
    assert "Rate limited" in coordinator._classify_http_error(err)


def test_classify_http_error_503(coordinator):
    err = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=503)
    assert "Server error 503" in coordinator._classify_http_error(err)


def test_classify_http_error_other(coordinator):
    err = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=418)
    assert "HTTP error 418" in coordinator._classify_http_error(err)


@pytest.mark.asyncio
async def test_first_failure_logs_warning(hass, coordinator, caplog):
    """First consecutive failure logs at WARNING level."""
    import logging
    err = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=503)
    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(side_effect=err),
    ), caplog.at_level(logging.WARNING, logger="custom_components.mybuderus.coordinator"):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
    assert any("Server error 503" in r.message for r in caplog.records if r.levelno == logging.WARNING)


@pytest.mark.asyncio
async def test_second_failure_logs_debug(hass, coordinator, caplog):
    """Subsequent failures (after the first) log at DEBUG, not WARNING."""
    import logging
    coordinator._consecutive_failures = 1  # simulate prior failure
    err = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=503)
    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(side_effect=err),
    ), caplog.at_level(logging.DEBUG, logger="custom_components.mybuderus.coordinator"):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
    warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING and "Server error" in r.message]
    assert len(warning_msgs) == 0


@pytest.mark.asyncio
async def test_update_failed_message_includes_last_success(hass, coordinator):
    """UpdateFailed message includes last success context."""
    err = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=503)
    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(side_effect=err),
    ):
        with pytest.raises(UpdateFailed, match="last data: never"):
            await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_network_error_logs_warning(hass, coordinator, caplog):
    """Network errors log at WARNING on first occurrence."""
    import logging
    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(side_effect=aiohttp.ClientError("DNS failure")),
    ), caplog.at_level(logging.WARNING, logger="custom_components.mybuderus.coordinator"):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
    assert any("Network error" in r.message for r in caplog.records if r.levelno == logging.WARNING)


@pytest.mark.asyncio
async def test_outage_issue_created_at_threshold(hass, coordinator):
    """Outage repair issue is created once the threshold is crossed."""
    # With scan_interval=300 and threshold=3600: 12 failures crosses threshold
    coordinator._consecutive_failures = 11  # one more will cross
    err = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=503)
    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(side_effect=err),
    ), patch(
        "custom_components.mybuderus.coordinator.create_outage_issue"
    ) as mock_create:
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
    mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_outage_issue_not_created_before_threshold(hass, coordinator):
    """Outage repair issue is NOT created before threshold is crossed."""
    coordinator._consecutive_failures = 0  # first failure, well below 3600s
    err = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=503)
    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(side_effect=err),
    ), patch(
        "custom_components.mybuderus.coordinator.create_outage_issue"
    ) as mock_create:
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
    mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_success_sets_last_success_at(hass, coordinator):
    """Successful poll sets _last_success_at."""
    assert coordinator._last_success_at is None
    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(return_value=BULK_DATA),
    ):
        await coordinator._async_update_data()
    assert coordinator._last_success_at is not None


@pytest.mark.asyncio
async def test_success_resets_failure_count(hass, coordinator):
    """Successful poll resets _consecutive_failures to 0."""
    coordinator._consecutive_failures = 5
    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(return_value=BULK_DATA),
    ):
        await coordinator._async_update_data()
    assert coordinator._consecutive_failures == 0


@pytest.mark.asyncio
async def test_success_clears_outage_issue(hass, coordinator):
    """Successful poll clears an active outage repair issue."""
    coordinator._outage_issue_active = True
    coordinator._consecutive_failures = 12
    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(return_value=BULK_DATA),
    ), patch(
        "custom_components.mybuderus.coordinator.clear_outage_issue"
    ) as mock_clear:
        await coordinator._async_update_data()
    mock_clear.assert_called_once_with(hass, coordinator._entry.entry_id)
    assert coordinator._outage_issue_active is False


@pytest.mark.asyncio
async def test_success_logs_recovery(hass, coordinator, caplog):
    """Recovery after failures is logged at INFO."""
    import logging
    coordinator._consecutive_failures = 3
    with patch(
        "custom_components.mybuderus.coordinator.get_bulk",
        new=AsyncMock(return_value=BULK_DATA),
    ), caplog.at_level(logging.INFO, logger="custom_components.mybuderus.coordinator"):
        await coordinator._async_update_data()
    assert any("Recovered after 3" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_auth_failure_clears_outage_issue(hass, coordinator):
    """Auth failure (ConfigEntryAuthFailed) clears any active outage issue."""
    coordinator._outage_issue_active = True
    coordinator._expires_at = time.time() - 10  # expired

    error = aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=401)
    with patch(
        "custom_components.mybuderus.coordinator.refresh_access_token",
        new=AsyncMock(side_effect=error),
    ), patch(
        "custom_components.mybuderus.coordinator.clear_outage_issue"
    ) as mock_clear:
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()
    mock_clear.assert_called_once()
    assert coordinator._outage_issue_active is False
