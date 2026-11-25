"""Number platform: settings of the operating modes (as in the web UI's settings dialogs)."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import VarioventConfigEntry, VarioventCoordinator
from .entity import VarioventEntity
from .helpers import async_write
from .pyvariovent.models import ModeSetting

UNITS = {"%": PERCENTAGE, "h": UnitOfTime.HOURS}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VarioventConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        ModeSettingNumber(coordinator, uid, setting)
        for uid, v in coordinator.data.ventilators.items()
        if not v.is_repeater
        for setting in v.available_mode_settings
    )


class ModeSettingNumber(VarioventEntity, NumberEntity):
    """One value of an operating mode's settings."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_step = 1

    def __init__(self, coordinator: VarioventCoordinator, uid: int, setting: ModeSetting) -> None:
        super().__init__(coordinator, uid, setting.key)
        self.setting = setting
        self._attr_translation_key = setting.key
        self._attr_native_min_value = setting.minimum
        self._attr_native_max_value = setting.maximum
        self._attr_native_unit_of_measurement = UNITS.get(setting.unit) if setting.unit else None

    @property
    def native_value(self) -> float | None:
        v = self.ventilator
        return v.p(self.setting.index) if v else None

    async def async_set_native_value(self, value: float) -> None:
        # Values of one mode are saved together and validated like in the web UI
        # (e.g. "back below" must stay under "raise above"); violations raise
        # ValueError, which async_write turns into an error message.
        changes = {self.setting.key: int(value)}
        mode = self.setting.mode
        await async_write(
            self,
            lambda c: c.set_mode_settings(self.uid, mode, changes),
            lambda dev: dev.with_mode_settings(mode, changes),
        )
