"""Fan platform: one fan per ventilator (on/off, 5 levels, Betriebsart as preset)."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .pyvariovent.models import FAN_LEVEL_MAX, OperatingMode, P

from .const import SELECTABLE_MODES
from .coordinator import VarioventConfigEntry
from .entity import VarioventEntity
from .helpers import async_write, set_level

PRESET_MODES = [m for m in SELECTABLE_MODES if m != OperatingMode.OFF]
SPEED_COUNT = FAN_LEVEL_MAX + 1  # levels 0..4 -> 20 %, 40 %, ... 100 %


async def async_setup_entry(
    hass: HomeAssistant, entry: VarioventConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        VarioventFan(coordinator, uid)
        for uid, v in coordinator.data.ventilators.items()
        if not v.is_repeater
    )


class VarioventFan(VarioventEntity, FanEntity):
    """A ventilator."""

    _attr_name = None
    _attr_translation_key = "ventilator"
    _attr_speed_count = SPEED_COUNT
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator, uid: int) -> None:
        super().__init__(coordinator, uid, "fan")

    @property
    def is_on(self) -> bool | None:
        v = self.ventilator
        return None if v is None else v.mode != OperatingMode.OFF

    @property
    def percentage(self) -> int | None:
        v = self.ventilator
        if v is None or v.fan_level is None:
            return None
        if not self.is_on:
            return 0
        return round((v.fan_level + 1) * 100 / SPEED_COUNT)

    @property
    def preset_modes(self) -> list[str]:
        v = self.ventilator
        return [m for m in v.allowed_modes if m in PRESET_MODES] if v else PRESET_MODES

    @property
    def preset_mode(self) -> str | None:
        v = self.ventilator
        return v.mode if v and v.mode in PRESET_MODES else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        v = self.ventilator
        return {"fan_level": v.fan_level, "active_mode": v.active_mode} if v else {}

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        level = min(FAN_LEVEL_MAX, max(0, math.ceil(percentage * SPEED_COUNT / 100) - 1))
        await set_level(self, level)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self._set_mode(preset_mode)

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any
    ) -> None:
        if preset_mode:
            await self._set_mode(preset_mode)
        elif not self.is_on and not percentage:
            await self._set_mode(self._resume_mode())
        if percentage:
            # a fan level also switches an 'aus' / schedule device into manual operation
            await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_mode(OperatingMode.OFF)

    def _resume_mode(self) -> str:
        """Mode to use when switching on: the device-confirmed mode if it is a real
        operating mode, else a sensible manual mode."""
        v = self.ventilator
        confirmed = v.p(P.MODE_CONFIRMED) if v else None
        if v and confirmed in v.allowed_modes and confirmed != OperatingMode.OFF:
            return confirmed
        return v.mode_for_fan_level if v else OperatingMode.NORMAL

    async def _set_mode(self, mode: str) -> None:
        await async_write(self, lambda c: c.set_mode(self.uid, mode), lambda v: v.with_mode(mode))
