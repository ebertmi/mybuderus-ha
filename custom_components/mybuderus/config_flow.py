"""Config flow for myBuderus."""
import time
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import get_gateways
from .auth import build_auth_url, exchange_code, extract_code, generate_pkce_pair
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, MIN_SCAN_INTERVAL


class MyBuderusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for myBuderus."""

    VERSION = 1

    def __init__(self) -> None:
        self._code_verifier: str = ""
        self._auth_url: str = ""
        self._token_data: dict = {}
        self._gateway_id: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Show auth URL and code input field."""
        if not self._auth_url:
            code_verifier, code_challenge = generate_pkce_pair()
            self._code_verifier = code_verifier
            self._auth_url = build_auth_url(code_challenge)

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                code = extract_code(user_input["auth_code"])
            except ValueError:
                errors["auth_code"] = "invalid_code"
            else:
                session = async_get_clientsession(self.hass)
                try:
                    self._token_data = await exchange_code(
                        session, code, self._code_verifier
                    )
                    gateways = await get_gateways(
                        session, self._token_data["access_token"]
                    )
                    self._gateway_id = gateways[0]["deviceId"]
                except (aiohttp.ClientResponseError, IndexError, KeyError):
                    errors["base"] = "cannot_connect"
                else:
                    return await self.async_step_config()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("auth_code"): str}),
            description_placeholders={"auth_url": self._auth_url},
            errors=errors,
        )

    async def async_step_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: Name and polling interval."""
        if user_input is not None:
            entry_data = {
                "access_token": self._token_data["access_token"],
                "refresh_token": self._token_data["refresh_token"],
                "expires_at": time.time() + self._token_data.get("expires_in", 3600),
                "gateway_id": self._gateway_id,
            }
            return self.async_create_entry(
                title=user_input["name"],
                data=entry_data,
                options={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]},
            )

        return self.async_show_form(
            step_id="config",
            data_schema=vol.Schema({
                vol.Required("name", default="myBuderus"): str,
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    int, vol.Range(min=MIN_SCAN_INTERVAL)
                ),
            }),
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when token refresh fails."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show re-auth form with new login link."""
        if not self._auth_url:
            code_verifier, code_challenge = generate_pkce_pair()
            self._code_verifier = code_verifier
            self._auth_url = build_auth_url(code_challenge)

        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            try:
                code = extract_code(user_input["auth_code"])
                token_data = await exchange_code(session, code, self._code_verifier)
            except (ValueError, aiohttp.ClientResponseError):
                errors["auth_code"] = "invalid_code"
            else:
                entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        "access_token": token_data["access_token"],
                        "refresh_token": token_data["refresh_token"],
                        "expires_at": time.time() + token_data.get("expires_in", 3600),
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required("auth_code"): str}),
            description_placeholders={"auth_url": self._auth_url},
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> "MyBuderusOptionsFlow":
        return MyBuderusOptionsFlow(config_entry)


class MyBuderusOptionsFlow(OptionsFlow):
    """Options flow for adjusting the polling interval."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self._config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    int, vol.Range(min=MIN_SCAN_INTERVAL)
                ),
            }),
        )
