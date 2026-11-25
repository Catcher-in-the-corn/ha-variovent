"""Binary sensor platform: filter change due, device fault."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .pyvariovent.models import Ventilator

from .coordinator import VarioventConfigEntry, VarioventCoordinator
from .entity import VarioventEntity


@dataclass(frozen=True, kw_only=True)
class VentilatorBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[Ventilator], bool]


BINARY_SENSORS = (
    VentilatorBinaryDescription(
        key="filter_due",
        translation_key="filter_due",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda v: v.filter_due,
    ),
    VentilatorBinaryDescription(
        key="fault",
        translation_key="fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda v: v.has_error,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VarioventConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        VentilatorBinarySensor(coordinator, uid, d)
        for uid, v in coordinator.data.ventilators.items()
        if not v.is_repeater
        for d in BINARY_SENSORS
    )


class VentilatorBinarySensor(VarioventEntity, BinarySensorEntity):
    """A problem indicator of one ventilator."""

    entity_description: VentilatorBinaryDescription

    def __init__(
        self,
        coordinator: VarioventCoordinator,
        uid: int,
        description: VentilatorBinaryDescription,
    ) -> None:
        super().__init__(coordinator, uid, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        v = self.ventilator
        return self.entity_description.value_fn(v) if v else None
