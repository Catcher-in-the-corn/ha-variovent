"""End-to-end tests of the Home Assistant integration against a fake spot."""

from __future__ import annotations

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.variovent.const import DOMAIN

USER_INPUT = {CONF_HOST: "192.0.2.10", CONF_USERNAME: "admin", CONF_PASSWORD: "secret"}


async def _setup(hass: HomeAssistant, unique_id: str = "0000000001") -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, unique_id=unique_id)
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


async def test_config_flow_spot_refuses(hass: HomeAssistant, fake_spot) -> None:
    """Reachable spot, valid login, but the user lacks a right: show the spot's message."""
    fake_spot.denied = {"lueftungsgeraeteReadRange"}
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["errors"] == {"base": "spot_error"}
    assert "Berechtigung" in result["description_placeholders"]["error"]


async def test_config_flow_restricted_user_without_spot_details(hass: HomeAssistant, fake_spot) -> None:
    fake_spot.denied = {"raspberrypiReadEingeschraenkt"}
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "900000000001"


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


# Without a readable spot serial the entry's unique_id is the lowest ventilator serial
# (see test_config_flow_restricted_user_without_spot_details).
VENTILATOR_SERIAL_AS_ID = "900000000001"


async def test_setup_without_spot_serial_keeps_all_ventilators(hass: HomeAssistant, fake_spot) -> None:
    """The spot's device must not take the identifier of the ventilator whose serial it borrows."""
    entry = await _setup(hass, VENTILATOR_SERIAL_AS_ID)

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 8  # spot + 7 ventilators
    spot = next(d for d in devices if d.via_device_id is None)
    assert all(d.via_device_id == spot.id for d in devices if d is not spot)
    assert (DOMAIN, VENTILATOR_SERIAL_AS_ID) not in spot.identifiers
    assert len(hass.states.async_entity_ids("fan")) == 7


async def test_old_spot_device_is_migrated(hass: HomeAssistant, fake_spot) -> None:
    """An install from <= 0.4.0 keeps its spot device (id, area) under the new identifier."""
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, unique_id=VENTILATOR_SERIAL_AS_ID)
    entry.add_to_hass(hass)
    reg = dr.async_get(hass)
    old = reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, VENTILATOR_SERIAL_AS_ID)},
        manufacturer="Variovent", model="DUO-Live Spot", name="Variovent Spot",
    )
    reg.async_update_device(old.id, area_id="technik")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    spot = reg.async_get(old.id)
    assert spot.identifiers == {(DOMAIN, f"spot_{VENTILATOR_SERIAL_AS_ID}")}
    assert spot.area_id == "technik"
    devices = dr.async_entries_for_config_entry(reg, entry.entry_id)
    assert len(devices) == 8
    assert all(d.via_device_id == spot.id for d in devices if d.id != spot.id)
    # spot entities keep their unique_id (same entity ids, history stays) and stay on the spot
    ent = er.async_get(hass)
    eid = ent.async_get_entity_id("sensor", DOMAIN, f"{VENTILATOR_SERIAL_AS_ID}_error_count")
    assert eid is not None
    assert ent.async_get(eid).device_id == spot.id


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


def _entity_id(hass: HomeAssistant, domain: str, unique_id: str) -> str:
    from homeassistant.helpers import entity_registry as er

    entity_id = er.async_get(hass).async_get_entity_id(domain, DOMAIN, unique_id)
    assert entity_id, unique_id
    return entity_id


async def test_humidity_mode_settings(hass: HomeAssistant, fake_spot) -> None:
    await _setup(hass)
    rise = _entity_id(hass, "number", "900000000001_humidity_rise")
    fall = _entity_id(hass, "number", "900000000001_humidity_fall")
    assert float(hass.states.get(rise).state) == 50  # values of the recorded fixture
    assert float(hass.states.get(fall).state) == 45

    fake_spot.calls.clear()
    await hass.services.async_call("number", "set_value", {"entity_id": rise, "value": 60}, blocking=True)
    call = next(c for c in fake_spot.calls if c[0] == "lueftungsgeraeteParameterBAEinstellungenUpdate")
    params = call[1]
    assert params[1][0].endswith("UserSession/2592594343")  # session is the 2nd parameter
    assert params[2][1] == "feuchteabluft"
    sent = params[0][1].items[0].fields[6].fields
    assert (int(sent[13]), int(sent[14]), int(sent[15]), int(sent[17])) == (60, 45, 70, 1)

    # "back below" must stay under "raise above": refused before anything is sent
    fake_spot.calls.clear()
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("number", "set_value", {"entity_id": fall, "value": 80}, blocking=True)
    assert not [c for c in fake_spot.calls if c[0] == "lueftungsgeraeteParameterBAEinstellungenUpdate"]


async def test_mode_settings_per_device_type(hass: HomeAssistant, fake_spot) -> None:
    from homeassistant.helpers import entity_registry as er

    await _setup(hass)
    reg = er.async_get(hass)
    assert reg.async_get_entity_id("number", DOMAIN, "900000000006_party_duration")  # DUO-Live
    assert not reg.async_get_entity_id("number", DOMAIN, "900000000001_party_duration")  # MONO-Smart
    aq = _entity_id(hass, "number", "900000000001_air_quality_rise")
    assert float(hass.states.get(aq).state) == 900

    fake_spot.calls.clear()
    await hass.services.async_call("number", "set_value", {"entity_id": aq, "value": 1000}, blocking=True)
    call = next(c for c in fake_spot.calls if c[0] == "lueftungsgeraeteParameterBAEinstellungenUpdate")
    assert call[1][2][1] == "luftguete"
    value = call[1][0][1].items[0].fields[6].fields[20]
    assert int(value) == 1000 and type(value).__name__ == "JInteger"


async def test_relogin_after_login_elsewhere(hass: HomeAssistant, fake_spot) -> None:
    """A login in the web UI invalidates our session; the next poll must recover."""
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    logins = fake_spot.logins

    fake_spot.stale_session_calls = 1
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success
    assert fake_spot.logins == logins + 1
    assert hass.states.get("fan.raum_1").state != STATE_UNAVAILABLE
    assert not list(hass.config_entries.flow.async_progress())  # no reauth prompt


async def test_unload(hass: HomeAssistant, fake_spot) -> None:
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
