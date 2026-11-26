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
from .entity import legacy_spot_identifier, spot_device_info, spot_identifier

PLATFORMS = [Platform.BINARY_SENSOR, Platform.FAN, Platform.NUMBER, Platform.SELECT, Platform.SENSOR]


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
    registry = dr.async_get(hass)
    _migrate_spot_identifier(registry, entry, coordinator)
    spot = registry.async_get_or_create(
        config_entry_id=entry.entry_id, **spot_device_info(coordinator)
    )
    coordinator.spot_device_id = spot.id

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


def _migrate_spot_identifier(
    registry: dr.DeviceRegistry, entry: VarioventConfigEntry, coordinator: VarioventCoordinator
) -> None:
    """Move the spot device of an install <= 0.4.0 to the prefixed identifier.

    Keeps the device (id, area, name) so nothing changes for the user. Only the spot can
    hold the old identifier: it is the only device of the entry without a parent, and a
    ventilator with that serial was refused by HA before.
    """
    if _find_device(registry, spot_identifier(coordinator), entry.entry_id):
        return
    old = _find_device(registry, legacy_spot_identifier(coordinator), entry.entry_id)
    if old and old.via_device_id is None:
        registry.async_update_device(old.id, new_identifiers={spot_identifier(coordinator)})


def _find_device(
    registry: dr.DeviceRegistry, identifier: tuple[str, str], entry_id: str
) -> dr.DeviceEntry | None:
    """Device of this entry with the identifier (HA >= 2026.10 has a per-entry lookup)."""
    if hasattr(registry, "async_get_device_by_identifier"):
        return registry.async_get_device_by_identifier(identifier, entry_id)
    device = registry.async_get_device(identifiers={identifier})
    return device if device and entry_id in device.config_entries else None


async def _async_reload(hass: HomeAssistant, entry: VarioventConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: VarioventConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
