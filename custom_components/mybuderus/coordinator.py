"""DataUpdateCoordinator for myBuderus."""
import logging
import time
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import get_bulk
from .auth import refresh_access_token
from .const import DOMAIN, OUTAGE_REPAIR_THRESHOLD
from .repairs import clear_outage_issue, create_outage_issue

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

        self._last_success_at: float | None = None
        self._consecutive_failures: int = 0
        self._outage_issue_active: bool = False

        expires_in_min = max(0, (self._expires_at - time.time()) / 60)
        _LOGGER.info("Coordinator initialized, token expires in %dm", int(expires_in_min))

    @property
    def gateway_id(self) -> str:
        """Return the gateway device ID."""
        return self._gateway_id

    def _format_last_success(self) -> str:
        """Return human-readable elapsed time since last successful poll."""
        if self._last_success_at is None:
            return "never"
        elapsed = time.time() - self._last_success_at
        if elapsed < 3600:
            return f"{int(elapsed / 60)}m ago"
        if elapsed < 86400:
            return f"{int(elapsed / 3600)}h {int((elapsed % 3600) / 60)}m ago"
        days = int(elapsed / 86400)
        hours = int((elapsed % 86400) / 3600)
        return f"{days}d {hours}h ago"

    def _classify_http_error(self, err: aiohttp.ClientResponseError) -> str:
        """Return a descriptive message for an HTTP error status code."""
        if err.status == 403:
            return "Permission denied — token may lack required scopes"
        if err.status == 404:
            return "Endpoint not found — gateway ID or API URL may be wrong"
        if err.status == 429:
            return "Rate limited by API"
        if err.status >= 500:
            return f"Server error {err.status} — API may be temporarily unavailable"
        return f"HTTP error {err.status}"

    def _handle_auth_failure(self) -> None:
        """Log auth failure and clear any active outage issue."""
        _LOGGER.error(
            "Auth failure — re-auth required (token expired at %s)",
            datetime.fromtimestamp(self._expires_at).strftime("%Y-%m-%d %H:%M"),
        )
        if self._outage_issue_active:
            clear_outage_issue(self.hass, self._entry.entry_id)
            self._outage_issue_active = False

    def _record_failure(self, error_msg: str) -> None:
        """Increment failure counter, log, and create outage issue if threshold reached."""
        self._consecutive_failures += 1
        if self._consecutive_failures == 1:
            _LOGGER.warning(
                "%s (failure %d, last data: %s)",
                error_msg,
                self._consecutive_failures,
                self._format_last_success(),
            )
        else:
            _LOGGER.debug(
                "%s (failure %d, last data: %s)",
                error_msg,
                self._consecutive_failures,
                self._format_last_success(),
            )

        if (
            self._consecutive_failures * self.update_interval.total_seconds()
            >= OUTAGE_REPAIR_THRESHOLD
        ):
            if not self._outage_issue_active:
                _LOGGER.warning(
                    "Outage repair issue created — %d consecutive failures, no data since %s",
                    self._consecutive_failures,
                    self._format_last_success(),
                )
                self._outage_issue_active = True
            create_outage_issue(
                self.hass, self._entry.entry_id, self._last_success_at, error_msg
            )

    async def _do_token_refresh(self) -> None:
        """Refresh the access token and persist new tokens to config entry."""
        try:
            token_data = await refresh_access_token(self._session, self._refresh_token)
        except aiohttp.ClientResponseError as err:
            if err.status in (400, 401):
                raise ConfigEntryAuthFailed("Refresh token expired") from err
            raise UpdateFailed(f"Token refresh failed: {err}") from err

        self._access_token = token_data["access_token"]
        self._refresh_token = token_data.get("refresh_token", self._refresh_token)
        self._expires_at = time.time() + token_data.get("expires_in", 3600)

        _LOGGER.info(
            "Token refreshed successfully, expires in %dm",
            int(token_data.get("expires_in", 3600) / 60),
        )
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
            try:
                await self._do_token_refresh()
            except ConfigEntryAuthFailed:
                self._handle_auth_failure()
                raise
            except UpdateFailed as err:
                self._record_failure(str(err))
                raise

        try:
            result = await get_bulk(self._session, self._access_token, self._gateway_id)
        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                try:
                    await self._do_token_refresh()
                except ConfigEntryAuthFailed:
                    self._handle_auth_failure()
                    raise
                try:
                    result = await get_bulk(
                        self._session, self._access_token, self._gateway_id
                    )
                except aiohttp.ClientResponseError as retry_err:
                    self._handle_auth_failure()
                    raise ConfigEntryAuthFailed("Authentication failed") from retry_err
            else:
                error_msg = self._classify_http_error(err)
                self._record_failure(error_msg)
                raise UpdateFailed(
                    f"{error_msg} — last data: {self._format_last_success()}"
                ) from err
        except aiohttp.ClientError as err:
            error_msg = f"Network error — could not reach API"
            self._record_failure(f"{error_msg}: {err}")
            raise UpdateFailed(
                f"Network error: {err} — last data: {self._format_last_success()}"
            ) from err

        # Success path
        was_failing = self._consecutive_failures > 0
        prev_failures = self._consecutive_failures
        self._last_success_at = time.time()
        self._consecutive_failures = 0

        if was_failing:
            _LOGGER.info("Recovered after %d consecutive failures", prev_failures)
        if self._outage_issue_active:
            _LOGGER.info("Outage repair issue cleared — data successfully retrieved")
            clear_outage_issue(self.hass, self._entry.entry_id)
            self._outage_issue_active = False
        _LOGGER.info("Data retrieved successfully (%d resources)", len(result))
        return result
