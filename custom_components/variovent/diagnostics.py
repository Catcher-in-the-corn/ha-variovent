"""Diagnostics: credentials and personal data redacted, raw values kept for bug reports."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .pyvariovent.gwt import GwtObject, unbox

from .coordinator import VarioventConfigEntry

TO_REDACT = {CONF_PASSWORD, CONF_USERNAME, CONF_HOST, "serial", "dwelling", "name"}


def _raw(obj: GwtObject) -> list[Any]:
    return [f"<{f.name}>" if isinstance(f, GwtObject) else repr(unbox(f)) for f in obj.fields]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: VarioventConfigEntry
) -> dict[str, Any]:
    data = entry.runtime_data.data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "firmware": data.firmware,
        "firmware_available": data.firmware_available,
        "error_count": data.error_count,
        "ventilators": [
            {
                "state": async_redact_data(v.as_dict(), TO_REDACT),
                "raw_params": _raw(v.params),
            }
            for v in data.ventilators.values()
        ],
    }
