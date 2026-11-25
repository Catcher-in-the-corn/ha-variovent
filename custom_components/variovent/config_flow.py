"""Config flow for Variovent."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .pyvariovent import AuthError, CannotConnect, VarioventClient, VariventError

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, MIN_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def _validate(hass, host: str, username: str, password: str) -> str:
    """Log in once; returns a stable unique id for the spot."""
    session = async_create_clientsession(hass, cookie_jar=aiohttp.CookieJar(unsafe=True))
    client = VarioventClient(host, username, password, session=session)
    if not await client.ping():
        raise CannotConnect(host)
    await client.login()
    data = await client.fetch_data()
    try:
        return (await client.read_spot_info()).serial
    except VariventError as err:
        # restricted users may not read the spot details; fall back to the
        # lowest ventilator serial, which is just as stable for a given installation
        _LOGGER.debug("spot serial not readable (%s), using ventilator serial", err)
        serials = sorted(v.serial for v in data.ventilators.values())
        if not serials:
            raise
        return serials[0]


async def _check(
    hass, host: str, username: str, password: str
) -> tuple[str | None, dict[str, str], dict[str, str]]:
    """Validate credentials; returns (unique_id, errors, description placeholders)."""
    try:
        return await _validate(hass, host, username, password), {}, {}
    except AuthError:
        return None, {"base": "invalid_auth"}, {}
    except CannotConnect as err:
        _LOGGER.warning("Spot at %s not reachable: %s", host, err)
        return None, {"base": "cannot_connect"}, {}
    except VariventError as err:
        # reachable and logged in, but the spot refused a request (e.g. missing user rights)
        _LOGGER.warning("Spot at %s refused a request: %s", host, err)
        return None, {"base": "spot_error"}, {"error": str(err)}


class VarioventConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"error": ""}
        if user_input is not None:
            unique_id, errors, found = await _check(
                self.hass, user_input[CONF_HOST], user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            placeholders.update(found)
            if unique_id:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured(updates={CONF_HOST: user_input[CONF_HOST]})
                return self.async_create_entry(title=f"Variovent ({user_input[CONF_HOST]})", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"error": ""}
        entry = self._get_reauth_entry()
        if user_input is not None:
            unique_id, errors, found = await _check(
                self.hass, entry.data[CONF_HOST], user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            placeholders.update(found)
            if unique_id:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=entry.data.get(CONF_USERNAME, "")): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"error": ""}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            unique_id, errors, found = await _check(
                self.hass, user_input[CONF_HOST], user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            placeholders.update(found)
            if unique_id:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input or dict(entry.data)),
            errors=errors,
            description_placeholders=placeholders,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return VarioventOptionsFlow()


class VarioventOptionsFlow(OptionsFlow):
    """Polling interval."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds()))
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=3600)
                    )
                }
            ),
        )
