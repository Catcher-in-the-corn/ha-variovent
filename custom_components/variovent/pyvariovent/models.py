"""Typed view on the spot's raw DTOs.

Field indices refer to the wire order of firmware V2.08 (see layouts.py) and
were mapped by comparing live data with the spot's own web UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .gwt import GwtObject, JShort, unbox


class OperatingMode(StrEnum):
    """Betriebsarten as used by the spot."""

    OFF = "aus"
    SCHEDULE = "wochenplan"
    NORMAL = "normalbetrieb"
    AUTO = "automatik"
    SUMMER = "sommer"
    PARTY = "party"
    AWAY = "abwesenheit"
    SUPPLY = "zuluft"
    EXHAUST = "fortluft"
    HUMIDITY = "feuchteabluft"
    AIR_QUALITY = "luftguete"


FAN_LEVEL_MIN = 0
FAN_LEVEL_MAX = 4


class LG:
    """Indices in Lueftungsgeraet (15 fields)."""

    SERIAL = 0
    OPERATING_HOURS = 1  # hours since last filter change
    NAME = 2
    PARTNER_UID = 5  # DUO partner device
    PARAMS = 6
    ROOM_TYPE = 8
    SERIAL_STR = 10
    UID = 12
    DWELLING = 13


class P:
    """Indices in LueftungsgeraetParameter (155 fields)."""

    FEUCHTEABLUFT_ACTIVE = 16
    MODE_SET = 26  # eingestellte Betriebsart (incl. 'wochenplan' / 'aus')
    MODE_PREVIOUS = 27
    MODE_ACTIVE = 28  # aktuell wirksame Betriebsart
    HUMIDITY = 29
    HUMIDITY_2 = 30
    HUMIDITY_SENSOR_MISSING = 32
    FILTER_INTERVAL = 33  # hours, sign encodes "reset pending"
    ERROR_FLAG_A = 34
    SCHEDULES = 54
    FAN_LEVEL_2 = 108
    FAN_LEVEL = 109  # Short 0..4, written by the "Lüfterstufe ändern" dialog
    DEVICE_TYPE = 110
    AIR_QUALITY_THRESHOLD_MODERATE = 112
    AIR_QUALITY_THRESHOLD_POOR = 113
    AIR_QUALITY_SENSOR_PRESENT = 118
    AIR_QUALITY = 119  # shown by the UI only as traffic light
    SIGNAL = 127
    TEMP_INT = 132
    ERROR_FLAG_B = 133
    TEMP_FRAC = 134
    TEMP_SENSOR_PRESENT = 135
    TEMP2_INT = 136
    ERROR_FLAG_C = 137
    TEMP2_FRAC = 138
    TEMP2_SENSOR_PRESENT = 139


DEVICE_TYPES = {
    1: "DUO-Live",
    2: "DUO-Live Silent (Links)",
    3: "DUO-Live Silent (Rechts)",
    10: "DUO-Smart",
    11: "DUO-Smart Silent",
    20: "MONO-Smart",
    21: "MONO-Smart Silent",
    23: "MONO-Smart Silent Abluft",
    30: "Repeater",
}
DEVICE_TYPE_REPEATER = 30

AIR_QUALITY_GOOD = "good"
AIR_QUALITY_MODERATE = "moderate"
AIR_QUALITY_POOR = "poor"


def _v(obj: GwtObject, idx: int) -> Any:
    return unbox(obj.fields[idx])


def _temp(p: GwtObject, i: int, f: int) -> float | None:
    whole, frac = _v(p, i), _v(p, f)
    if whole is None:
        return None
    frac = max(0, min(99, frac or 0))
    return round(whole + (frac / 100 if whole >= 0 else -frac / 100), 1)


@dataclass
class Ventilator:
    """One Lüftungsgerät connected to the spot."""

    raw: GwtObject

    @property
    def params(self) -> GwtObject:
        return self.raw.fields[LG.PARAMS]

    def p(self, idx: int) -> Any:
        return _v(self.params, idx)

    # identity -----------------------------------------------------------
    @property
    def uid(self) -> int:
        return _v(self.raw, LG.UID)

    @property
    def serial(self) -> str:
        return _v(self.raw, LG.SERIAL_STR) or str(_v(self.raw, LG.SERIAL))

    @property
    def name(self) -> str:
        return _v(self.raw, LG.NAME) or f"Lüfter {self.uid}"

    @property
    def room_type(self) -> str | None:
        return _v(self.raw, LG.ROOM_TYPE) or None

    @property
    def dwelling(self) -> str | None:
        return _v(self.raw, LG.DWELLING) or None

    @property
    def partner_uid(self) -> int | None:
        return _v(self.raw, LG.PARTNER_UID)

    @property
    def device_type(self) -> int | None:
        return self.p(P.DEVICE_TYPE)

    @property
    def model(self) -> str:
        return DEVICE_TYPES.get(self.device_type or -1, f"Typ {self.device_type}")

    # state --------------------------------------------------------------
    @property
    def mode(self) -> str | None:
        return self.p(P.MODE_SET)

    @property
    def active_mode(self) -> str | None:
        return self.p(P.MODE_ACTIVE)

    @property
    def fan_level(self) -> int | None:
        return self.p(P.FAN_LEVEL)

    @property
    def is_on(self) -> bool:
        return self.mode != OperatingMode.OFF or bool(self.fan_level)

    # sensors ------------------------------------------------------------
    @property
    def temperature(self) -> float | None:
        if self.p(P.TEMP_SENSOR_PRESENT) == 0:
            return None
        return _temp(self.params, P.TEMP_INT, P.TEMP_FRAC)

    @property
    def temperature_2(self) -> float | None:
        if self.p(P.TEMP2_SENSOR_PRESENT) == 0 or not self.p(P.TEMP2_INT):
            return None
        return _temp(self.params, P.TEMP2_INT, P.TEMP2_FRAC)

    @property
    def humidity(self) -> int | None:
        return self.p(P.HUMIDITY)

    @property
    def is_repeater(self) -> bool:
        return self.device_type == DEVICE_TYPE_REPEATER

    @property
    def sensors_active(self) -> bool:
        """The web UI hides sensor tiles while the effective mode is 'aus'."""
        return self.active_mode != OperatingMode.OFF and self.mode != OperatingMode.OFF

    @property
    def air_quality(self) -> int | None:
        if self.p(P.AIR_QUALITY_SENSOR_PRESENT) != 1:
            return None
        value = self.p(P.AIR_QUALITY)
        return value if value is not None and value >= 0 else None

    @property
    def air_quality_level(self) -> str | None:
        value = self.air_quality
        if value is None:
            return None
        if value >= (self.p(P.AIR_QUALITY_THRESHOLD_POOR) or 1200):
            return AIR_QUALITY_POOR
        if value >= (self.p(P.AIR_QUALITY_THRESHOLD_MODERATE) or 800):
            return AIR_QUALITY_MODERATE
        return AIR_QUALITY_GOOD

    @property
    def signal(self) -> int | None:
        return self.p(P.SIGNAL)

    @property
    def operating_hours(self) -> int | None:
        return _v(self.raw, LG.OPERATING_HOURS)

    @property
    def filter_interval(self) -> int | None:
        value = self.p(P.FILTER_INTERVAL)
        return abs(value) if value is not None else None

    @property
    def filter_remaining_hours(self) -> int | None:
        if self.filter_interval is None or self.operating_hours is None:
            return None
        return self.filter_interval - self.operating_hours

    @property
    def filter_due(self) -> bool:
        remaining = self.filter_remaining_hours
        return remaining is not None and remaining <= 0

    @property
    def has_error(self) -> bool:
        return any(self.p(i) == 1 for i in (P.ERROR_FLAG_A, P.ERROR_FLAG_B, P.ERROR_FLAG_C))

    # mutation helpers (return modified copies of the raw DTO) -----------------
    def with_fan_level(self, level: int) -> GwtObject:
        if not FAN_LEVEL_MIN <= level <= FAN_LEVEL_MAX:
            raise ValueError(f"fan level must be {FAN_LEVEL_MIN}..{FAN_LEVEL_MAX}")
        self.params.fields[P.FAN_LEVEL] = JShort(level)
        return self.raw

    def with_mode(self, mode: str) -> GwtObject:
        self.params.fields[P.MODE_SET] = str(OperatingMode(mode))
        return self.raw

    def as_dict(self) -> dict[str, Any]:
        keys = (
            "uid", "serial", "name", "model", "room_type", "dwelling", "partner_uid",
            "mode", "active_mode", "fan_level", "temperature", "temperature_2", "humidity",
            "air_quality", "air_quality_level", "sensors_active", "signal", "operating_hours", "filter_interval", "filter_remaining_hours",
            "filter_due", "has_error",
        )  # fmt: skip
        return {k: getattr(self, k) for k in keys}


@dataclass(frozen=True)
class SpotInfo:
    name: str
    series: str | None
    serial: str


@dataclass
class SpotData:
    """Everything the integration polls in one go."""

    ventilators: dict[int, Ventilator]
    error_count: int | None
    firmware: str | None
    firmware_available: str | None
