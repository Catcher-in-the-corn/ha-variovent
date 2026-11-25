"""Capture real spot responses and store anonymized copies as test fixtures.

Usage (credentials from .env.local):
    python scripts/capture_fixtures.py --host 192.168.1.10
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pyvariovent import VarioventClient  # noqa: E402
from pyvariovent.__main__ import _load_env_file  # noqa: E402
from pyvariovent.client import find_all  # noqa: E402
from pyvariovent.gwt import parse_response  # noqa: E402
from pyvariovent.models import Ventilator  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def _js_escape(text: str) -> str:
    """How GWT escapes non-ASCII characters in the response string table."""
    return "".join(c if ord(c) < 128 else f"\\u{ord(c):04X}" for c in text)


def anonymize(body: str) -> str:
    devices = [Ventilator(d) for d in find_all(parse_response(body), "Lueftungsgeraet")]
    replacements: dict[str, str] = {}
    for i, v in enumerate(devices, 1):
        replacements[v.name] = f"Raum {i}"
        replacements[v.serial] = f"9000000000{i:02d}"
        if v.dwelling:
            replacements[v.dwelling] = "Wohnung"
        numeric = int(v.raw.fields[0])
        body = re.sub(rf"(?<=[\[,]){numeric}(?=,)", str(900000000 + i), body)

    def fix(match: re.Match[str]) -> str:
        inner = match.group(1)
        for original, new in replacements.items():
            if inner in (original, _js_escape(original), _js_escape(original).lower()):
                return f'"{new}"'
        return match.group(0)

    body = re.sub(r'"((?:[^"\\]|\\.)*)"', fix, body)
    leaks = [k for k in replacements if k and (k in body or _js_escape(k) in body)]
    if leaks:
        raise SystemExit(f"anonymization incomplete: {len(leaks)} values left")
    return body


async def capture(host: str) -> dict[str, str]:
    captured: dict[str, str] = {}
    async with VarioventClient(host, os.environ["VARIOVENT_USER"], os.environ["VARIOVENT_PASSWORD"]) as client:
        await client.login()
        http = client._http()
        original_post = http.post
        last: dict[str, str] = {}

        class Recorder:
            def __init__(self, cm):
                self._cm = cm

            async def __aenter__(self):
                resp = await self._cm.__aenter__()
                last["body"] = await resp.text(encoding="utf-8")
                return resp

            async def __aexit__(self, *exc):
                return await self._cm.__aexit__(*exc)

        http.post = lambda *a, **k: Recorder(original_post(*a, **k))  # type: ignore[method-assign]
        for name, call in (
            ("devices", client.read_devices),
            ("error_count", client.read_error_count),
            ("versions", client.read_versions),
            ("ping", client.ping),
        ):
            await call()
            captured[name] = last["body"]
    return captured


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    args = parser.parse_args()
    _load_env_file(str(ROOT / ".env.local"))
    captured = asyncio.run(capture(args.host))
    captured["devices"] = anonymize(captured["devices"])
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for name, body in captured.items():
        (FIXTURES / f"{name}.txt").write_text(body, encoding="utf-8", newline="\n")
        print("wrote", name)


if __name__ == "__main__":
    main()
