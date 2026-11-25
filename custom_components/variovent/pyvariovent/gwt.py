"""Minimal GWT-RPC (protocol version 7) codec.

Only what the DUO-Live spot needs: a request writer and a response reader that
decode every value into Python objects which can be serialized back unchanged
(needed because the spot's update calls expect the complete DTO).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Any

from .layouts import ENUMS, LAYOUTS

RPC_VERSION = 7

SIG_STRING = "java.lang.String/2004016611"
SIG_INTEGER = "java.lang.Integer/3438268394"
SIG_LONG = "java.lang.Long/4227064769"
SIG_SHORT = "java.lang.Short/551743396"
SIG_BOOLEAN = "java.lang.Boolean/476441737"
SIG_DOUBLE = "java.lang.Double/858496421"
SIG_DATE = "java.util.Date/3385151746"
SIG_SQL_DATE = "java.sql.Date/730999118"
SIG_SQL_TIME = "java.sql.Time/1816797103"
SIG_TIMESTAMP = "java.sql.Timestamp/3040052672"
SIG_VECTOR = "java.util.Vector/3057315478"
SIG_STACK = "java.util.Stack/1346942793"
SIG_HASHMAP = "java.util.HashMap/1797211028"
SIG_LINKED_HASHMAP = "java.util.LinkedHashMap/3008245022"

_B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789$_"


class GwtError(Exception):
    """Raised for malformed payloads or server side exceptions (//EX)."""


# --------------------------------------------------------------------------- values


class JInteger(int):
    sig = SIG_INTEGER


class JShort(int):
    sig = SIG_SHORT


class JLong(int):
    sig = SIG_LONG


@dataclass
class JDate:
    """java.util.Date / java.sql.* – millis since epoch."""

    millis: int
    sig: str = SIG_DATE
    nanos: int | None = None  # only for java.sql.Timestamp

    @property
    def datetime(self) -> dt.datetime:
        return dt.datetime.fromtimestamp(self.millis / 1000, tz=dt.UTC)


@dataclass
class JEnum:
    sig: str
    ordinal: int


@dataclass
class JList:
    """A java.util.Vector (or Stack) keeping its Java type."""

    items: list[Any] = field(default_factory=list)
    sig: str = SIG_VECTOR

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


@dataclass
class JMap:
    items: list[tuple[Any, Any]] = field(default_factory=list)
    sig: str = SIG_HASHMAP
    access_order: bool = False

    def as_dict(self) -> dict:
        return dict(self.items)


@dataclass
class GwtObject:
    """An instance of one of the spot's DTO classes (de.zsa...shared.*)."""

    sig: str
    fields: list[Any]

    @property
    def name(self) -> str:
        return self.sig.rsplit(".", 1)[-1].split("/")[0]

    def __getitem__(self, i: int) -> Any:
        return self.fields[i]

    def __setitem__(self, i: int, v: Any) -> None:
        self.fields[i] = v


def unbox(v: Any) -> Any:
    """Turn wrapper values into plain Python values (for display / HA states)."""
    if isinstance(v, (JInteger, JShort, JLong)):
        return int(v)
    if isinstance(v, JDate):
        return v.datetime
    if isinstance(v, JEnum):
        return v.ordinal
    if isinstance(v, JList):
        return [unbox(x) for x in v.items]
    if isinstance(v, JMap):
        return {unbox(k): unbox(x) for k, x in v.items}
    return v


# --------------------------------------------------------------------------- longs


def long_to_b64(value: int) -> str:
    value &= (1 << 64) - 1
    if value == 0:
        return "A"
    out = []
    while value:
        out.append(_B64[value & 63])
        value >>= 6
    return "".join(reversed(out))


def b64_to_long(s: str) -> int:
    value = 0
    for ch in s:
        value = (value << 6) | _B64.index(ch)
    value &= (1 << 64) - 1
    return value - (1 << 64) if value >= 1 << 63 else value


# --------------------------------------------------------------------------- writer


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("|", "\\!").replace("\0", "\\0")


class RequestWriter:
    def __init__(self, module_base: str, policy: str) -> None:
        self._strings: list[str] = []
        self._index: dict[str, int] = {}
        self._tokens: list[str] = []
        self.write_string(module_base)
        self.write_string(policy)

    # primitives
    def _string_index(self, s: str | None) -> int:
        if s is None:
            return 0
        if s not in self._index:
            self._strings.append(s)
            self._index[s] = len(self._strings)
        return self._index[s]

    def write_int(self, v: int) -> None:
        self._tokens.append(str(int(v)))

    def write_string(self, s: str | None) -> None:
        self.write_int(self._string_index(s))

    def write_long(self, v: int) -> None:
        self._tokens.append(long_to_b64(v))

    # objects
    def write_object(self, v: Any) -> None:  # noqa: C901
        if v is None:
            self.write_int(0)
            return
        if isinstance(v, GwtObject):
            self.write_string(v.sig)
            if v.sig in ENUMS:
                self.write_int(v.fields[0])
                return
            layout = LAYOUTS.get(v.sig)
            if layout is None:
                raise GwtError(f"no layout for {v.sig}")
            if len(layout) != len(v.fields):
                raise GwtError(f"{v.sig}: expected {len(layout)} fields")
            for kind, fv in zip(layout, v.fields):
                if kind == "s":
                    self.write_string(fv)
                else:
                    self.write_object(fv)
            return
        if isinstance(v, JEnum):
            self.write_string(v.sig)
            self.write_int(v.ordinal)
        elif isinstance(v, bool):
            self.write_string(SIG_BOOLEAN)
            self.write_int(1 if v else 0)
        elif isinstance(v, JLong):
            self.write_string(SIG_LONG)
            self.write_long(v)
        elif isinstance(v, JShort):
            self.write_string(SIG_SHORT)
            self.write_int(v)
        elif isinstance(v, int):  # JInteger and plain int
            self.write_string(SIG_INTEGER)
            self.write_int(v)
        elif isinstance(v, float):
            self.write_string(SIG_DOUBLE)
            self._tokens.append(repr(v))
        elif isinstance(v, str):
            self.write_string(SIG_STRING)
            self.write_string(v)
        elif isinstance(v, JDate):
            self.write_string(v.sig)
            self.write_long(v.millis)
            if v.sig == SIG_TIMESTAMP:
                self.write_int(v.nanos or 0)
        elif isinstance(v, (JList, list)):
            items = v.items if isinstance(v, JList) else v
            self.write_string(v.sig if isinstance(v, JList) else SIG_VECTOR)
            self.write_int(len(items))
            for item in items:
                self.write_object(item)
        elif isinstance(v, JMap):
            self.write_string(v.sig)
            if v.sig == SIG_LINKED_HASHMAP:
                self.write_int(1 if v.access_order else 0)
            self.write_int(len(v.items))
            for k, item in v.items:
                self.write_object(k)
                self.write_object(item)
        else:
            raise GwtError(f"cannot serialize {type(v)!r}")

    def payload(self) -> str:
        parts = [str(RPC_VERSION), "0", str(len(self._strings))]
        parts += [_escape(s) for s in self._strings]
        parts += self._tokens
        return "|".join(parts) + "|"


def build_request(
    module_base: str,
    policy: str,
    interface: str,
    method: str,
    params: list[tuple[str, Any]],
) -> str:
    """params: list of (declared type signature, value)."""
    w = RequestWriter(module_base, policy)
    w.write_string(interface)
    w.write_string(method)
    w.write_int(len(params))
    for sig, _ in params:
        w.write_string(sig)
    for sig, value in params:
        if sig == SIG_STRING:
            # declared String parameters are written as a bare string-table index
            if value is not None and not isinstance(value, str):
                raise GwtError("String parameter expected")
            w.write_string(value)
        else:
            w.write_object(value)
    return w.payload()


# --------------------------------------------------------------------------- reader

_JS_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}


def _parse_js_array(text: str) -> list[Any]:  # noqa: C901
    """Parse the JS array literal of a GWT response (numbers, strings, arrays)."""
    text = text.replace("].concat([", ",")
    pos = 0
    n = len(text)

    def skip_ws() -> None:
        nonlocal pos
        while pos < n and text[pos] in " \t\r\n":
            pos += 1

    def parse_value() -> Any:
        nonlocal pos
        skip_ws()
        ch = text[pos]
        if ch == "[":
            pos += 1
            out = []
            skip_ws()
            if text[pos] == "]":
                pos += 1
                return out
            while True:
                out.append(parse_value())
                skip_ws()
                if text[pos] == ",":
                    pos += 1
                    continue
                if text[pos] == "]":
                    pos += 1
                    return out
                raise GwtError(f"unexpected {text[pos]!r} at {pos}")
        if ch in "'\"":
            quote = ch
            pos += 1
            buf = []
            while True:
                c = text[pos]
                if c == quote:
                    pos += 1
                    return "".join(buf)
                if c == "\\":
                    e = text[pos + 1]
                    if e == "u":
                        buf.append(chr(int(text[pos + 2 : pos + 6], 16)))
                        pos += 6
                    elif e == "x":
                        buf.append(chr(int(text[pos + 2 : pos + 4], 16)))
                        pos += 4
                    else:
                        buf.append(_JS_ESCAPES.get(e, e))
                        pos += 2
                    continue
                buf.append(c)
                pos += 1
        m = re.compile(r"-?[0-9.eE+-]+|NaN|Infinity|-Infinity|true|false|null").match(text, pos)
        if not m:
            raise GwtError(f"unexpected {ch!r} at {pos}")
        pos = m.end()
        tok = m.group(0)
        if tok in ("true", "false"):
            return tok == "true"
        if tok == "null":
            return None
        if tok in ("NaN", "Infinity", "-Infinity"):
            return float(tok)
        f = float(tok)
        return int(f) if f.is_integer() and "." not in tok and "e" not in tok.lower() else f

    return parse_value()


class ResponseReader:
    def __init__(self, data: list[Any]) -> None:
        if len(data) < 3:
            raise GwtError("response too short")
        version = data[-1]
        if version != RPC_VERSION:
            raise GwtError(f"unsupported RPC version {version}")
        self._strings: list[str] = data[-3]
        self._data = data
        self._pos = len(data) - 3
        self._seen: list[Any] = []

    @property
    def remaining(self) -> int:
        return self._pos

    def _next(self) -> Any:
        self._pos -= 1
        if self._pos < 0:
            raise GwtError("read past end of payload")
        return self._data[self._pos]

    def read_int(self) -> int:
        return int(self._next())

    def read_string(self) -> str | None:
        idx = self.read_int()
        return self._strings[idx - 1] if idx > 0 else None

    def read_long(self) -> int:
        v = self._next()
        return b64_to_long(v) if isinstance(v, str) else int(v)

    def read_object(self) -> Any:  # noqa: C901
        idx = self.read_int()
        if idx < 0:
            return self._seen[-(idx + 1)]
        if idx == 0:
            return None
        sig = self._strings[idx - 1]
        slot = len(self._seen)
        self._seen.append(None)

        value: Any
        if sig == SIG_INTEGER:
            value = JInteger(self.read_int())
        elif sig == SIG_SHORT:
            value = JShort(self.read_int())
        elif sig == SIG_LONG:
            value = JLong(self.read_long())
        elif sig == SIG_BOOLEAN:
            value = bool(self.read_int())
        elif sig == SIG_DOUBLE:
            value = float(self._next())
        elif sig == SIG_STRING:
            value = self.read_string()
        elif sig in (SIG_DATE, SIG_SQL_DATE, SIG_SQL_TIME):
            value = JDate(self.read_long(), sig)
        elif sig == SIG_TIMESTAMP:
            value = JDate(self.read_long(), sig)
            value.nanos = self.read_int()
        elif sig in (SIG_VECTOR, SIG_STACK):
            value = JList([], sig)
            self._seen[slot] = value
            for _ in range(self.read_int()):
                value.items.append(self.read_object())
        elif sig in (SIG_HASHMAP, SIG_LINKED_HASHMAP):
            value = JMap([], sig)
            if sig == SIG_LINKED_HASHMAP:
                value.access_order = bool(self.read_int())
            self._seen[slot] = value
            for _ in range(self.read_int()):
                k = self.read_object()
                value.items.append((k, self.read_object()))
        elif sig in ENUMS:
            value = JEnum(sig, self.read_int())
        elif sig in LAYOUTS:
            value = GwtObject(sig, [])
            self._seen[slot] = value
            for kind in LAYOUTS[sig]:
                value.fields.append(self.read_string() if kind == "s" else self.read_object())
        else:
            raise GwtError(f"unknown type in response: {sig}")
        self._seen[slot] = value
        return value


def parse_response(body: str) -> Any:
    """Decode a GWT-RPC response body. Raises GwtError for //EX."""
    body = body.strip()
    if body.startswith("//OK"):
        reader = ResponseReader(_parse_js_array(body[4:]))
        value = reader.read_object()
        if reader.remaining:
            raise GwtError(f"{reader.remaining} unread tokens - layout mismatch?")
        return value
    if body.startswith("//EX"):
        try:
            exc = ResponseReader(_parse_js_array(body[4:])).read_object()
        except GwtError:
            exc = body[:300]
        if isinstance(exc, GwtObject):
            exc = f"{exc.name}: {exc.fields}"
        raise GwtError(f"server exception: {exc}")
    raise GwtError(f"unexpected response: {body[:200]}")
