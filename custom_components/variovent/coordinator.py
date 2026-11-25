"""Data update coordinator for a Variovent spot."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .pyvariovent import AuthError, VarioventClient, VariventError
from .pyvariovent.models import SpotData, SpotInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

type VarioventConfigEntry = ConfigEntry[VarioventCoordinator]


class VarioventCoordinator(DataUpdateCoordinator[SpotData]):
    """Polls the spot; all entities read from one snapshot."""

    config_entry: VarioventConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: VarioventConfigEntry,
        client: VarioventClient,
        interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {client.host}",
            update_interval=interval,
        )
        self.client = client
        self.spot_info: SpotInfo | None = None
        self.spot_device_id: str | None = None

    async def _async_setup(self) -> None:
        try:
            self.spot_info = await self.client.read_spot_info()
        except AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except VariventError as err:
            _LOGGER.debug("spot info unavailable: %s", err)

    async def _async_update_data(self) -> SpotData:
        try:
            return await self.client.fetch_data()
        except AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except VariventError as err:
            raise UpdateFailed(str(err)) from err
