"""DataUpdateCoordinator for myBuderus."""
import logging
import time
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import get_bulk
from .auth import refresh_access_token
from .const import DOMAIN

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

    @property
    def gateway_id(self) -> str:
        """Return the gateway device ID."""
        return self._gateway_id

    async def _do_token_refresh(self) -> None:
        """Refresh the access token and persist new tokens to config entry."""
        try:
            token_data = await refresh_access_token(self._session, self._refresh_token)
        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                raise ConfigEntryAuthFailed("Refresh token expired") from err
            raise UpdateFailed(f"Token refresh failed: {err}") from err

        self._access_token = token_data["access_token"]
        self._refresh_token = token_data.get("refresh_token", self._refresh_token)
        self._expires_at = time.time() + token_data.get("expires_in", 3600)

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
            await self._do_token_refresh()

        try:
            return await get_bulk(self._session, self._access_token, self._gateway_id)
        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                await self._do_token_refresh()
                try:
                    return await get_bulk(
                        self._session, self._access_token, self._gateway_id
                    )
                except aiohttp.ClientResponseError as retry_err:
                    raise ConfigEntryAuthFailed("Authentication failed") from retry_err
            raise UpdateFailed(f"API error: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Network error: {err}") from err
