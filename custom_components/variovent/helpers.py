"""Shared helpers for writing to the spot."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import HomeAssistantError

from .pyvariovent import VarioventClient, VariventError
from .pyvariovent.models import Ventilator

from .const import DOMAIN

if TYPE_CHECKING:
    from .entity import VarioventEntity


async def async_write(
    entity: VarioventEntity,
    action: Callable[[VarioventClient], Awaitable[Any]],
    optimistic: Callable[[Ventilator], Any],
) -> None:
    """Send a command, update the cached state optimistically, then refresh.

    The spot forwards commands by radio, so the confirmed state can lag a few seconds.
    """
    coordinator = entity.coordinator
    try:
        await action(coordinator.client)
    except ValueError as err:
        raise HomeAssistantError(str(err)) from err
    except VariventError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="command_failed", translation_placeholders={"error": str(err)}
        ) from err
    v = entity.ventilator
    if v is not None:
        try:
            optimistic(v)
        except ValueError:
            pass  # cached state is only cosmetic; the refresh below corrects it
        coordinator.async_update_listeners()
    await coordinator.async_request_refresh()


def _optimistic_level(level: int) -> Callable[[Ventilator], Any]:
    def apply(v: Ventilator) -> None:
        v.with_mode(v.mode_for_fan_level)
        v.with_fan_level(level)

    return apply


async def set_level(entity: VarioventEntity, level: int) -> None:
    """Set a fan level (the library switches 'aus'/schedule devices to manual mode)."""
    await async_write(entity, lambda c: c.set_fan_level(entity.uid, level), _optimistic_level(level))
