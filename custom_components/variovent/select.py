"""Select platform: Betriebsart and Lüfterstufe."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .pyvariovent.models import FAN_LEVEL_MAX, FAN_LEVEL_MIN

from .const import SELECTABLE_MODES
from .coordinator import VarioventConfigEntry
from .entity import VarioventEntity
from .helpers import async_write

FAN_LEVELS = [str(i) for i in range(FAN_LEVEL_MIN, FAN_LEVEL_MAX + 1)]


async def async_setup_entry(
    hass: HomeAssistant, entry: VarioventConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[SelectEntity] = []
    for uid, v in coordinator.data.ventilators.items():
        if v.is_repeater:
            continue
        entities += [ModeSelect(coordinator, uid), FanLevelSelect(coordinator, uid)]
    async_add_entities(entities)


class ModeSelect(VarioventEntity, SelectEntity):
    """Betriebsart."""

    _attr_translation_key = "mode"
    _attr_options = SELECTABLE_MODES

    def __init__(self, coordinator, uid: int) -> None:
        super().__init__(coordinator, uid, "mode")

    @property
    def current_option(self) -> str | None:
        v = self.ventilator
        return v.mode if v and v.mode in SELECTABLE_MODES else None

    async def async_select_option(self, option: str) -> None:
        await async_write(self, lambda c: c.set_mode(self.uid, option), lambda v: v.with_mode(option))


class FanLevelSelect(VarioventEntity, SelectEntity):
    """Lüfterstufe 0-4."""

    _attr_translation_key = "fan_level"
    _attr_options = FAN_LEVELS

    def __init__(self, coordinator, uid: int) -> None:
        super().__init__(coordinator, uid, "fan_level")

    @property
    def current_option(self) -> str | None:
        v = self.ventilator
        return str(v.fan_level) if v and v.fan_level is not None else None

    async def async_select_option(self, option: str) -> None:
        level = int(option)
        await async_write(self, lambda c: c.set_fan_level(self.uid, level), lambda v: v.with_fan_level(level))
