"""End-to-end tests of the Home Assistant integration against a fake spot."""

from __future__ import annotations

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.variovent.const import DOMAIN

USER_INPUT = {CONF_HOST: "192.0.2.10", CONF_USERNAME: "admin", CONF_PASSWORD: "secret"}


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, unique_id="0000000001")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_config_flow(hass: HomeAssistant, fake_spot) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "0000000001"


async def test_config_flow_bad_login(hass: HomeAssistant, fake_spot) -> None:
    fake_spot.fail_login = True
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_config_flow_offline(hass: HomeAssistant, fake_spot) -> None:
    fake_spot.offline = True
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_setup_creates_devices_and_entities(hass: HomeAssistant, fake_spot) -> None:
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 8  # spot + 7 ventilators
    assert sum(1 for d in devices if d.via_device_id) == 7

    fans = hass.states.async_entity_ids("fan")
    assert len(fans) == 7
    on = [hass.states.get(f) for f in fans if hass.states.get(f).state == "on"]
    assert len(on) == 3  # three rooms run on their weekly schedule
    assert all(s.attributes["preset_mode"] == "wochenplan" for s in on)

    # sensors of switched-off devices are unavailable, like in the web UI
    temps = [hass.states.get(e) for e in hass.states.async_entity_ids("sensor") if e.endswith("_temperature")]
    assert len([s for s in temps if s.state != STATE_UNAVAILABLE]) == 3

    filter_due = [e for e in hass.states.async_entity_ids("binary_sensor") if "filter" in e]
    assert sum(hass.states.get(e).state == "on" for e in filter_due) == 3


def _sent(calls, method: str) -> list:
    """Devices sent with each call of `method`, in order."""
    return [c[1][0][1].items[0] for c in calls if c[0] == method]


MODE_UPDATE = "lueftungsgeraeteBetriebsartUpdate"
LEVEL_UPDATE = "lueftungsgeraeteLuefterstufeUpdate"


async def test_set_mode_and_level(hass: HomeAssistant, fake_spot) -> None:
    await _setup(hass)
    fan = "fan.raum_1"  # MONO-Smart, currently 'aus'

    fake_spot.calls.clear()
    await hass.services.async_call("fan", "turn_off", {"entity_id": fan}, blocking=True)
    assert _sent(fake_spot.calls, MODE_UPDATE)[0].fields[6].fields[26] == "aus"

    fake_spot.calls.clear()
    await hass.services.async_call(
        "fan", "set_preset_mode", {"entity_id": fan, "preset_mode": "abwesenheit"}, blocking=True
    )
    assert _sent(fake_spot.calls, MODE_UPDATE)[0].fields[6].fields[26] == "abwesenheit"

    # the spot rejects fan levels while 'aus': the mode is switched to normal first
    fake_spot.calls.clear()
    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.raum_1_fan_level", "option": "3"}, blocking=True
    )
    methods = [c[0] for c in fake_spot.calls if c[0] in (MODE_UPDATE, LEVEL_UPDATE)]
    assert methods == [MODE_UPDATE, LEVEL_UPDATE]
    assert _sent(fake_spot.calls, MODE_UPDATE)[0].fields[6].fields[26] == "normalbetrieb"
    assert int(_sent(fake_spot.calls, LEVEL_UPDATE)[0].fields[6].fields[109]) == 3


async def test_modes_depend_on_device_type(hass: HomeAssistant, fake_spot) -> None:
    await _setup(hass)
    mono = hass.states.get("select.raum_1_operating_mode").attributes["options"]
    duo = hass.states.get("select.raum_6_operating_mode").attributes["options"]
    assert "party" not in mono and "automatik" not in mono and "sommer" not in mono
    assert "party" in duo and "automatik" in duo
    assert "party" not in hass.states.get("fan.raum_1").attributes["preset_modes"]

    # a mode the device does not support is refused before anything is sent
    fake_spot.calls.clear()
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "fan", "set_preset_mode", {"entity_id": "fan.raum_1", "preset_mode": "party"}, blocking=True
        )
    assert not _sent(fake_spot.calls, MODE_UPDATE)


async def test_unload(hass: HomeAssistant, fake_spot) -> None:
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
