"""Sensor platform."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .pyvariovent.models import (
    AIR_QUALITY_GOOD,
    AIR_QUALITY_MODERATE,
    AIR_QUALITY_POOR,
    SpotData,
    Ventilator,
)

from .const import SELECTABLE_MODES
from .coordinator import VarioventConfigEntry, VarioventCoordinator
from .entity import VarioventEntity, VarioventSpotEntity


def _not_repeater(v: Ventilator) -> bool:
    return not v.is_repeater


@dataclass(frozen=True, kw_only=True)
class VentilatorSensorDescription(SensorEntityDescription):
    value_fn: Callable[[Ventilator], Any]
    # Sensor values freeze while a device is switched off; the web UI hides them then.
    needs_active: bool = False
    exists_fn: Callable[[Ventilator], bool] = _not_repeater


VENTILATOR_SENSORS: tuple[VentilatorSensorDescription, ...] = (
    VentilatorSensorDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda v: v.temperature,
        needs_active=True,
    ),
    VentilatorSensorDescription(
        key="temperature_2",
        translation_key="temperature_2",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda v: v.temperature_2,
        needs_active=True,
        exists_fn=lambda v: v.temperature_2 is not None,
    ),
    VentilatorSensorDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.humidity,
        needs_active=True,
    ),
    VentilatorSensorDescription(
        key="air_quality",
        translation_key="air_quality",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v: v.air_quality,
        needs_active=True,
        exists_fn=lambda v: not v.is_repeater and v.air_quality is not None,
    ),
    VentilatorSensorDescription(
        key="air_quality_level",
        translation_key="air_quality_level",
        device_class=SensorDeviceClass.ENUM,
        options=[AIR_QUALITY_GOOD, AIR_QUALITY_MODERATE, AIR_QUALITY_POOR],
        value_fn=lambda v: v.air_quality_level,
        needs_active=True,
        exists_fn=lambda v: not v.is_repeater and v.air_quality is not None,
    ),
    VentilatorSensorDescription(
        key="active_mode",
        translation_key="active_mode",
        device_class=SensorDeviceClass.ENUM,
        options=SELECTABLE_MODES,
        value_fn=lambda v: v.active_mode if v.active_mode in SELECTABLE_MODES else None,
    ),
    VentilatorSensorDescription(
        key="filter_remaining",
        translation_key="filter_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=lambda v: v.filter_remaining_hours,
    ),
    VentilatorSensorDescription(
        key="operating_hours",
        translation_key="operating_hours",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda v: v.operating_hours,
    ),
    VentilatorSensorDescription(
        key="signal",
        translation_key="signal",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda v: v.signal,
        exists_fn=lambda v: True,
    ),
)


@dataclass(frozen=True, kw_only=True)
class SpotSensorDescription(SensorEntityDescription):
    value_fn: Callable[[SpotData], Any]


SPOT_SENSORS: tuple[SpotSensorDescription, ...] = (
    SpotSensorDescription(
        key="error_count",
        translation_key="error_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.error_count,
    ),
    SpotSensorDescription(
        key="firmware_available",
        translation_key="firmware_available",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.firmware_available,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VarioventConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [SpotSensor(coordinator, d) for d in SPOT_SENSORS]
    for uid, v in coordinator.data.ventilators.items():
        entities += [
            VentilatorSensor(coordinator, uid, d) for d in VENTILATOR_SENSORS if d.exists_fn(v)
        ]
    async_add_entities(entities)


class VentilatorSensor(VarioventEntity, SensorEntity):
    """A value of one ventilator."""

    entity_description: VentilatorSensorDescription

    def __init__(
        self,
        coordinator: VarioventCoordinator,
        uid: int,
        description: VentilatorSensorDescription,
    ) -> None:
        super().__init__(coordinator, uid, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        if not self.entity_description.needs_active:
            return True
        v = self.ventilator
        return v is not None and v.sensors_active

    @property
    def native_value(self) -> Any:
        v = self.ventilator
        return self.entity_description.value_fn(v) if v else None


class SpotSensor(VarioventSpotEntity, SensorEntity):
    """A value of the spot itself."""

    entity_description: SpotSensorDescription

    def __init__(self, coordinator: VarioventCoordinator, description: SpotSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data
        return self.entity_description.value_fn(data) if data else None
