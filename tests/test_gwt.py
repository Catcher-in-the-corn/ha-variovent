"""Codec tests against anonymized real responses of a spot (firmware V2.08)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyvariovent.client import MAIN_SERVICE, SIG_LUEFTUNGSGERAET, find_all, result_ok
from pyvariovent.gwt import (
    SIG_STRING,
    SIG_VECTOR,
    GwtError,
    JList,
    JShort,
    ResponseReader,
    _parse_js_array,
    b64_to_long,
    build_request,
    long_to_b64,
    parse_response,
)
from pyvariovent.models import AIR_QUALITY_MODERATE, OperatingMode, Ventilator

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / f"{name}.txt").read_text(encoding="utf-8")


@pytest.fixture
def ventilators() -> list[Ventilator]:
    return [Ventilator(d) for d in find_all(parse_response(load("devices")), "Lueftungsgeraet")]


@pytest.mark.parametrize("value", [0, 1, -1, 63, 64, 1795617286214, -(2**63), 2**63 - 1])
def test_long_roundtrip(value: int) -> None:
    assert b64_to_long(long_to_b64(value)) == value


def test_known_longs() -> None:
    assert b64_to_long("P__________") == -1
    assert b64_to_long("A") == 0


def test_ping_response() -> None:
    result = parse_response(load("ping"))
    assert result.name == "MyResult"
    assert result_ok(result)


def test_device_list(ventilators: list[Ventilator]) -> None:
    assert len(ventilators) == 7
    assert {v.name for v in ventilators} == {f"Raum {i}" for i in range(1, 8)}
    by_uid = {v.uid: v for v in ventilators}
    # DUO pairs point at each other
    for v in ventilators:
        if v.partner_uid:
            assert by_uid[v.partner_uid].partner_uid == v.uid


def test_ventilator_values(ventilators: list[Ventilator]) -> None:
    for v in ventilators:
        assert v.mode in set(OperatingMode)
        assert v.fan_level in range(5)
        assert v.model != f"Typ {v.device_type}"
        assert v.filter_interval == 2160
        assert 0 <= v.signal <= 100
        assert v.temperature is None or 5 < v.temperature < 40
    duo = [v for v in ventilators if v.model == "DUO-Live"]
    assert duo and duo[0].temperature_2 is not None
    # sensors only count as live while the device is not switched off
    for v in ventilators:
        assert v.sensors_active == (v.mode != OperatingMode.OFF)


def test_air_quality_level(ventilators: list[Ventilator]) -> None:
    v = ventilators[0]
    v.params.fields[119] = type(v.params.fields[119])(850)
    assert v.air_quality_level == AIR_QUALITY_MODERATE


def test_active_mode(ventilators: list[Ventilator]) -> None:
    """Active mode = scheduled mode under a weekly schedule, else the set mode."""
    for v in ventilators:
        if v.mode == OperatingMode.SCHEDULE:
            assert v.active_mode == v.p(28)  # betriebsart_wochenplan, the concrete mode
            assert v.active_mode != OperatingMode.SCHEDULE
        else:
            assert v.active_mode == v.mode  # e.g. an off device is actively off


def test_serial_is_serial_not_radio_address(ventilators: list[Ventilator]) -> None:
    for v in ventilators:
        assert v.serial == v.raw.fields[10]  # seriennr, not adresse (field 0)
        assert v.serial != str(v.raw.fields[0])


def test_humidity_requires_sensor(ventilators: list[Ventilator]) -> None:
    v = ventilators[0]
    assert v.humidity is not None
    v.params.fields[31] = type(v.params.fields[31])(0)  # feuchtesensor1_ok = 0
    assert v.humidity is None


def _reread(payload: str) -> list:
    """Decode a request payload with the reader by turning it into response form."""
    tokens = payload.rstrip("|").split("|")
    count = int(tokens[2])
    strings = tokens[3 : 3 + count]
    rest = tokens[3 + count :]
    return strings, rest


def test_request_roundtrip_of_device(ventilators: list[Ventilator]) -> None:
    """Serialize a modified device and decode it again with the response reader."""
    v = ventilators[0]
    raw = v.with_fan_level(3)
    payload = build_request(
        "http://spot/zsalivespotwebapp/",
        MAIN_SERVICE[1],
        MAIN_SERVICE[2],
        "lueftungsgeraeteLuefterstufeUpdate",
        [(SIG_VECTOR, JList([raw]))],
    )
    strings, rest = _reread(payload)
    # skip module base, policy, interface, method, param count, param type
    values = rest[6:]
    # a response is read backwards: reverse the token stream and append the string table
    data = [t if not t.lstrip("-").isdigit() else int(t) for t in reversed(values)]
    reader = ResponseReader([*data, strings, 0, 7])
    decoded = reader.read_object()
    assert decoded.items[0].sig == SIG_LUEFTUNGSGERAET
    again = Ventilator(decoded.items[0])
    assert again.fan_level == 3
    assert again.as_dict() == v.as_dict()
    assert isinstance(again.params.fields[109], JShort)


def test_string_params_are_bare_indices() -> None:
    payload = build_request("b/", "P", "I", "m", [(SIG_STRING, "a|b")])
    assert payload == "7|0|6|b/|P|I|m|java.lang.String/2004016611|a\\!b|1|2|3|4|1|5|6|"


def test_invalid_mode_rejected(ventilators: list[Ventilator]) -> None:
    with pytest.raises(ValueError):
        ventilators[0].with_mode("turbo")
    with pytest.raises(ValueError):
        ventilators[0].with_fan_level(5)


def test_exception_response() -> None:
    with pytest.raises(GwtError):
        parse_response('//EX[2,1,["java.lang.IllegalArgumentException/1755012560","boom"],0,7]')


def test_js_array_parser() -> None:
    assert _parse_js_array("[1,'a',\"b\\u00E4\",[2]].concat([3])") == [1, "a", "bä", [2], 3]
