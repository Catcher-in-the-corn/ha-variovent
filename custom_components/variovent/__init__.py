"""The Variovent DUO-Live integration."""

from __future__ import annotations

from datetime import timedelta

import aiohttp

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .pyvariovent import VarioventClient

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .coordinator import VarioventConfigEntry, VarioventCoordinator
from .entity import spot_device_info

PLATFORMS = [Platform.BINARY_SENSOR, Platform.FAN, Platform.SELECT, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: VarioventConfigEntry) -> bool:
    """Set up a spot from a config entry."""
    # own session with a cookie jar that also accepts cookies from plain IP hosts
    session = async_create_clientsession(hass, cookie_jar=aiohttp.CookieJar(unsafe=True))
    client = VarioventClient(
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        session=session,
    )
    interval = timedelta(
        seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds())
    )
    coordinator = VarioventCoordinator(hass, entry, client, interval)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # register the spot first so ventilators can reference it as their parent device
    spot = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **spot_device_info(coordinator)
    )
    coordinator.spot_device_id = spot.id

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: VarioventConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: VarioventConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
