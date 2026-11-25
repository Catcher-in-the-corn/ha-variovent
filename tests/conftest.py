"""Shared fixtures: a fake spot that answers RPC calls with recorded responses."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / f"{name}.txt").read_text(encoding="utf-8")


class FakeSpot:
    """Replaces VarioventClient.raw_call; records write calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[tuple[str, Any]]]] = []
        self.fail_login = False
        self.offline = False
        self.stale_session_calls = 0  # next N session calls fail like after a login elsewhere
        self.denied: set[str] = set()  # methods the user has no right for
        self.logins = 0

    async def raw_call(self, client, service, method: str, params):  # noqa: ANN001
        from custom_components.variovent.pyvariovent.exceptions import CannotConnect
        from custom_components.variovent.pyvariovent.gwt import GwtObject, parse_response
        from custom_components.variovent.pyvariovent.layouts import PKG

        if self.offline:
            raise CannotConnect("offline")
        self.calls.append((method, params))
        if method in self.denied:
            from custom_components.variovent.pyvariovent.exceptions import VariventError

            raise VariventError(f"{method} failed: Sie besitzen nicht die Berechtigung")
        if method not in ("loginLiveSpot", "checkSpotIstDa") and self.stale_session_calls:
            from custom_components.variovent.pyvariovent.gwt import JEnum

            self.stale_session_calls -= 1
            result = parse_response(_load("ping"))
            code = result.fields[21]
            result.fields[21] = JEnum(code.sig, 1)  # error without any message text
            return result
        if method == "loginLiveSpot":
            self.logins += 1
            if self.fail_login:
                return parse_response(_load("ping"))  # MyResult without a session
            return GwtObject(PKG + "UserSession/2592594343", [None] * 23)
        if method == "raspberrypiReadEingeschraenkt":
            fields: list[Any] = [None] * 18
            fields[0], fields[1], fields[10] = "DUO-LiveSpot Lueftung", "X-Serie", "0000000001"
            return GwtObject(PKG + "Raspberrypi/1348886694", fields)
        responses = {
            "checkSpotIstDa": "ping",
            "lueftungsgeraeteReadRange": "devices",
            "lueftungsgeraeteReadByUids": "devices",
            "fehlermeldungenReadCount": "error_count",
            "versionInfosRead": "versions",
        }
        return parse_response(_load(responses.get(method, "ping")))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):  # noqa: ANN001
    yield


@pytest.fixture
def fake_spot():
    spot = FakeSpot()

    async def raw_call(client, service, method, params):  # noqa: ANN001
        return await spot.raw_call(client, service, method, params)

    with patch(
        "custom_components.variovent.pyvariovent.client.VarioventClient.raw_call",
        new=raw_call,
    ):
        yield spot
