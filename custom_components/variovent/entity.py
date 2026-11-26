"""Base entities for Variovent."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .pyvariovent.models import Ventilator

from .const import DOMAIN, MANUFACTURER
from .coordinator import VarioventCoordinator


def _spot_key(coordinator: VarioventCoordinator) -> str:
    """Stable key of the spot: the entry's unique_id. Prefix of the spot entities' unique_ids."""
    return coordinator.config_entry.unique_id or coordinator.config_entry.entry_id


def spot_identifier(coordinator: VarioventCoordinator) -> tuple[str, str]:
    """Device identifier of the spot.

    Prefixed because without a readable spot serial the entry's unique_id is the lowest
    ventilator serial (config_flow), which is also that ventilator's device identifier.
    Unprefixed, the ventilator resolved to the spot device and HA refused all its entities
    ("A device can not be its own via device").
    """
    return (DOMAIN, f"spot_{_spot_key(coordinator)}")


def legacy_spot_identifier(coordinator: VarioventCoordinator) -> tuple[str, str]:
    """Spot device identifier up to 0.4.0; migrated in async_setup_entry."""
    return (DOMAIN, _spot_key(coordinator))


def spot_device_info(coordinator: VarioventCoordinator) -> DeviceInfo:
    data = coordinator.data
    info = coordinator.spot_info
    return DeviceInfo(
        identifiers={spot_identifier(coordinator)},
        manufacturer=MANUFACTURER,
        model=f"DUO-Live Spot {info.series}" if info and info.series else "DUO-Live Spot",
        name="Variovent Spot",
        serial_number=info.serial if info else None,
        sw_version=data.firmware if data else None,
        configuration_url=f"http://{coordinator.client.host}/",
    )


def _via_spot(coordinator: VarioventCoordinator) -> dict:
    """Link a ventilator to the spot (HA >= 2026.x wants the registry id)."""
    if "via_device_id" in DeviceInfo.__annotations__ and coordinator.spot_device_id:
        return {"via_device_id": coordinator.spot_device_id}
    return {"via_device": spot_identifier(coordinator)}


class VarioventSpotEntity(CoordinatorEntity[VarioventCoordinator]):
    """Entity belonging to the spot (hub) device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VarioventCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{_spot_key(coordinator)}_{key}"
        self._attr_device_info = spot_device_info(coordinator)


class VarioventEntity(CoordinatorEntity[VarioventCoordinator]):
    """Entity belonging to one ventilator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VarioventCoordinator, uid: int, key: str) -> None:
        super().__init__(coordinator)
        self.uid = uid
        v = self.ventilator
        assert v is not None
        self._serial = v.serial
        self._attr_unique_id = f"{v.serial}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, v.serial)},
            manufacturer=MANUFACTURER,
            model=v.model,
            name=v.name,
            serial_number=v.serial,
            **_via_spot(coordinator),
        )

    @property
    def ventilator(self) -> Ventilator | None:
        data = self.coordinator.data
        return data.ventilators.get(self.uid) if data else None

    @property
    def available(self) -> bool:
        return super().available and self.ventilator is not None
