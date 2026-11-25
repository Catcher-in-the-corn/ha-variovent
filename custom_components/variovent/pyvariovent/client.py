"""Async client for the Variovent / ZSA "DUO-Live" spot web service."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .exceptions import AuthError, CannotConnect, VariventError
from .gwt import (
    SIG_BOOLEAN,
    SIG_INTEGER,
    SIG_STRING,
    SIG_VECTOR,
    GwtError,
    GwtObject,
    JInteger,
    JList,
    build_request,
    parse_response,
)
from .gwt import unbox
from .layouts import PKG
from .models import R, OperatingMode, SpotData, SpotInfo, Ventilator

_LOGGER = logging.getLogger(__name__)

MODULE_PATH = "/zsalivespotwebapp/"
# Strong names of the serialization policies of spot firmware V2.08
MAIN_SERVICE = ("zls", "7667AFBD29EB47DB0B6DD0B5B75C0395", "de.zsa.gwt.zsalivespotwebapp.client.ZSALiveSpotWebAppService")
LOGIN_SERVICE = ("login", "F606A4DD0AA9AB268637EB57BFD1BD08", "de.zsa.gwt.zsalivespotwebapp.client.LoginService")
PERMUTATION = "1B58ACDE1E4B99BD589D61EF5453E849"

SIG_USER_SESSION = PKG + "UserSession/2592594343"
SIG_LUEFTUNGSGERAET = PKG + "Lueftungsgeraet/3252019805"


class VarioventClient:
    """Thin RPC layer. Higher-level parsing lives in :mod:`pyvariovent.spot`."""

    def __init__(
        self,
        host: str,
        username: str | None = None,
        password: str | None = None,
        session: aiohttp.ClientSession | None = None,
        locale: str = "de",
        timeout: float = 15,
    ) -> None:
        self.host = host
        self.base = f"http://{host}{MODULE_PATH}"
        self.username = username
        self.password = password
        self.locale = locale
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._own_session = session is None
        self._session = session
        self._lock = asyncio.Lock()
        self.user_session: GwtObject | None = None

    async def __aenter__(self) -> VarioventClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self._own_session and self._session:
            await self._session.close()
            self._session = None

    def _http(self) -> aiohttp.ClientSession:
        if self._session is None:
            # unsafe=True: keep cookies for plain IP hosts
            self._session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
        return self._session

    # ------------------------------------------------------------------ raw RPC

    async def raw_call(
        self, service: tuple[str, str, str], method: str, params: list[tuple[str, Any]]
    ) -> Any:
        path, policy, interface = service
        body = build_request(self.base, policy, interface, method, params)
        headers = {
            "Content-Type": "text/x-gwt-rpc; charset=utf-8",
            "X-GWT-Permutation": PERMUTATION,
            "X-GWT-Module-Base": self.base,
        }
        _LOGGER.debug("RPC %s -> %s", method, body)
        try:
            async with self._lock, self._http().post(
                self.base + path, data=body.encode("utf-8"), headers=headers, timeout=self._timeout
            ) as resp:
                text = await resp.text(encoding="utf-8")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CannotConnect(f"{self.host}: {err}") from err
        _LOGGER.debug("RPC %s <- %s", method, text[:2000])
        if resp.status != 200 and not text.startswith("//EX"):
            raise CannotConnect(f"{method}: HTTP {resp.status}")
        try:
            return parse_response(text)
        except GwtError as err:
            raise VariventError(f"{method}: {err}") from err

    async def call(self, method: str, *params: tuple[str, Any], session_last: bool = True) -> Any:
        """Call a main-service method with the UserSession; re-login once if it expired."""
        for attempt in (1, 2):
            if self.user_session is None:
                await self.login()
            p = list(params)
            us = (SIG_USER_SESSION, self.user_session)
            p = p + [us] if session_last else [us] + p
            result = await self.raw_call(MAIN_SERVICE, method, p)
            if isinstance(result, GwtObject) and result.name == "MyResult":
                if result_session_expired(result) and attempt == 1:
                    _LOGGER.debug("%s: session expired, logging in again", method)
                    self.user_session = None
                    continue
                if not result_ok(result):
                    if result_session_expired(result):
                        raise AuthError(f"{method}: session rejected")
                    raise VariventError(f"{method} failed: {result_message(result)}")
            return result
        raise AuthError(f"{method}: session rejected")

    # ------------------------------------------------------------------ login

    async def login(self) -> GwtObject:
        if not self.username:
            raise AuthError("no credentials configured")
        result = await self.raw_call(
            LOGIN_SERVICE,
            "loginLiveSpot",
            [(SIG_STRING, self.username), (SIG_STRING, self.password or ""), (SIG_STRING, self.locale)],
        )
        session = find_first(result, "UserSession")
        if session is None:
            raise AuthError(f"login rejected: {describe(result)}")
        self.user_session = session
        return session

    # ------------------------------------------------------------------ unauthenticated

    async def ping(self) -> bool:
        res = await self.raw_call(MAIN_SERVICE, "checkSpotIstDa", [])
        return isinstance(res, GwtObject)

    async def server_time(self) -> Any:
        return await self.raw_call(MAIN_SERVICE, "getServerTime", [])

    # ------------------------------------------------------------------ reads

    async def read_devices(self, sort: str = "BEZEICHNUNG", count: int = 200) -> Any:
        return await self.call(
            "lueftungsgeraeteReadRange",
            (SIG_STRING, sort),
            (SIG_BOOLEAN, True),
            (SIG_INTEGER, JInteger(0)),
            (SIG_INTEGER, JInteger(count)),
            (SIG_BOOLEAN, False),
            session_last=False,
        )

    async def read_system_status(self) -> Any:
        return await self.call("kommunikationReadSystemparameterSystemStatus", session_last=False)

    async def read_error_count(self) -> Any:
        return await self.call("fehlermeldungenReadCount")

    async def read_errors(self, count: int = 50) -> Any:
        return await self.call(
            "fehlermeldungenReadRange",
            (SIG_STRING, "DATUM"),
            (SIG_BOOLEAN, False),
            (SIG_INTEGER, JInteger(0)),
            (SIG_INTEGER, JInteger(count)),
        )

    async def read_versions(self) -> Any:
        return await self.call("versionInfosRead")

    async def read_server_infos(self) -> Any:
        return await self.call("serverInfosRead")

    # ------------------------------------------------------------------ writes

    async def update_fan_level(self, devices: list[GwtObject]) -> Any:
        return await self.call("lueftungsgeraeteLuefterstufeUpdate", (SIG_VECTOR, JList(list(devices))))

    async def update_mode(self, devices: list[GwtObject]) -> Any:
        return await self.call("lueftungsgeraeteBetriebsartUpdate", (SIG_VECTOR, JList(list(devices))))


    # ------------------------------------------------------------------ high level

    async def fetch_data(self) -> SpotData:
        """Poll everything the Home Assistant integration needs."""
        devices = find_all(await self.read_devices(), "Lueftungsgeraet")
        ventilators = {v.uid: v for v in (self._ventilator(d) for d in devices)}
        error_count = firmware = available = None
        try:
            error_count = unbox(result_value(await self.read_error_count(), MR_INT))
            versions = find_first(await self.read_versions(), "VersionInfos")
            if versions is not None:
                available, firmware = versions.fields[0], versions.fields[1]
        except VariventError as err:  # optional data, don't fail the poll
            _LOGGER.debug("optional spot data unavailable: %s", err)
        return SpotData(ventilators, error_count, firmware, available)

    async def read_spot_info(self) -> SpotInfo:
        """Name, series and serial number of the spot itself."""
        rpi = find_first(await self.call("raspberrypiReadEingeschraenkt", (SIG_INTEGER, JInteger(1))), "Raspberrypi")
        if rpi is None:
            raise VariventError("spot info not available")
        return SpotInfo(name=rpi.fields[0] or "Variovent Spot", series=rpi.fields[1] or None, serial=rpi.fields[10])

    async def _fresh(self, uid: int) -> Ventilator:
        devices = find_all(
            await self.call("lueftungsgeraeteReadByUids", (SIG_VECTOR, JList([JInteger(uid)]))),
            "Lueftungsgeraet",
        )
        for d in devices:
            v = self._ventilator(d)
            if v.uid == uid:
                return v
        raise VariventError(f"ventilator {uid} not found")

    def _rights(self) -> dict[int, GwtObject]:
        """Per-device rights of the logged-in user (from the UserSession)."""
        if self.user_session is None:
            return {}
        return {
            unbox(r.fields[R.UID]): r
            for r in find_all(self.user_session.fields[SESSION_RIGHTS], "UserRechteLueftungsgeraete")
        }

    def _ventilator(self, raw: GwtObject) -> Ventilator:
        v = Ventilator(raw)
        v.rights = self._rights().get(v.uid)
        return v

    async def set_fan_level(self, uid: int, level: int) -> None:
        """Set a fan level; switches to a manual mode first if needed.

        The spot rejects level changes while the mode is 'aus' or 'wochenplan'.
        """
        v = await self._fresh(uid)
        target_mode = v.mode_for_fan_level
        if target_mode != v.mode:
            _LOGGER.debug("%s: switching to %s before setting fan level", v.name, target_mode)
            await self.update_mode([v.with_mode(target_mode)])
            v = await self._fresh(uid)
        await self.update_fan_level([v.with_fan_level(level)])

    async def set_mode(self, uid: int, mode: str | OperatingMode) -> None:
        v = await self._fresh(uid)
        await self.update_mode([v.with_mode(str(mode))])


# ---------------------------------------------------------------------- helpers

SESSION_RIGHTS = 20  # UserSession field holding the UserRechte object

# MyResult field indices
MR_INT = 10
MR_SESSION_EXPIRED = 13
MR_RESULT_CODE = 21
MR_MESSAGE = 26


def result_value(result: Any, idx: int) -> Any:
    return result.fields[idx] if isinstance(result, GwtObject) else None


def result_ok(result: GwtObject) -> bool:
    code = result.fields[MR_RESULT_CODE]
    return code is None or getattr(code, "ordinal", 0) == 0


def result_session_expired(result: GwtObject) -> bool:
    return result.fields[MR_SESSION_EXPIRED] is True


def result_message(result: GwtObject) -> str:
    texts = [x for x in walk(result) if isinstance(x, str) and x]
    return "; ".join(texts[:5]) or "unknown error"



def walk(value: Any):
    """Yield every nested value (depth first)."""
    seen: set[int] = set()
    stack = [value]
    while stack:
        v = stack.pop()
        if id(v) in seen:
            continue
        seen.add(id(v))
        yield v
        if isinstance(v, GwtObject):
            stack.extend(reversed(v.fields))
        elif isinstance(v, JList):
            stack.extend(reversed(v.items))
        elif hasattr(v, "items") and isinstance(getattr(v, "items"), list):
            for k, x in reversed(v.items):
                stack.extend([x, k])


def find_all(value: Any, name: str) -> list[GwtObject]:
    return [v for v in walk(value) if isinstance(v, GwtObject) and v.name == name]


def find_first(value: Any, name: str) -> GwtObject | None:
    found = find_all(value, name)
    return found[0] if found else None


def describe(value: Any, depth: int = 0, max_depth: int = 6) -> str:
    """Readable multi-line dump with field indices (used to map field meanings)."""
    from .gwt import unbox

    pad = "  " * depth
    if isinstance(value, GwtObject):
        if depth >= max_depth:
            return f"<{value.name}>"
        lines = [f"<{value.name}>"]
        for i, f in enumerate(value.fields):
            if f is None:
                continue
            lines.append(f"{pad}  [{i}] {describe(f, depth + 1, max_depth)}")
        return "\n".join(lines)
    if isinstance(value, JList):
        if not value.items:
            return "[]"
        return "[\n" + "\n".join(f"{pad}  - {describe(x, depth + 1, max_depth)}" for x in value.items) + f"\n{pad}]"
    return repr(unbox(value))
