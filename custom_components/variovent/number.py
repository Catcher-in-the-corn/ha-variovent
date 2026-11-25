"""Number platform: settings of the operating mode "Feuchte-Abluft" (humidity extraction)."""

from __future__ import annotations

from dataclasses import dataclass, replace

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import VarioventConfigEntry, VarioventCoordinator
from .entity import VarioventEntity
from .helpers import async_write
from .pyvariovent.models import HumiditySettings


@dataclass(frozen=True, kw_only=True)
class HumidityNumberDescription(NumberEntityDescription):
    field: str  # attribute of HumiditySettings


HUMIDITY_NUMBERS = (
    HumidityNumberDescription(
        key="humidity_rise",
        translation_key="humidity_rise",
        field="rise",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
    ),
    HumidityNumberDescription(
        key="humidity_fall",
        translation_key="humidity_fall",
        field="fall",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
    ),
    HumidityNumberDescription(
        key="humidity_exhaust",
        translation_key="humidity_exhaust",
        field="exhaust",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
    ),
    HumidityNumberDescription(
        key="humidity_steps",
        translation_key="humidity_steps",
        field="steps",
        native_min_value=1,
        native_max_value=3,
        native_step=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VarioventConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        HumiditySettingNumber(coordinator, uid, d)
        for uid, v in coordinator.data.ventilators.items()
        if "feuchteabluft" in v.allowed_modes and not v.is_repeater
        for d in HUMIDITY_NUMBERS
    )


class HumiditySettingNumber(VarioventEntity, NumberEntity):
    """One value of the humidity extraction settings."""

    entity_description: HumidityNumberDescription
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: VarioventCoordinator,
        uid: int,
        description: HumidityNumberDescription,
    ) -> None:
        super().__init__(coordinator, uid, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        v = self.ventilator
        return getattr(v.humidity_settings, self.entity_description.field) if v else None

    async def async_set_native_value(self, value: float) -> None:
        v = self.ventilator
        if v is None:
            return
        # the spot stores the four values together; keep the others unchanged
        # invalid combinations (e.g. "back below" >= "raise above") raise ValueError,
        # which async_write turns into an error message in the UI
        settings: HumiditySettings = replace(v.humidity_settings, **{self.entity_description.field: int(value)})
        await async_write(
            self,
            lambda c: c.set_humidity_settings(self.uid, settings),
            lambda dev: dev.with_humidity_settings(settings),
        )
