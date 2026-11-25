"""CLI for testing against a real spot.

    python -m pyvariovent --host 192.168.1.10 ping
    VARIOVENT_USER=.. VARIOVENT_PASSWORD=.. python -m pyvariovent --host 192.168.1.10 dump
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os

from .client import VarioventClient, describe


async def _main(args: argparse.Namespace) -> None:
    async with VarioventClient(
        args.host,
        args.user or os.environ.get("VARIOVENT_USER"),
        args.password or os.environ.get("VARIOVENT_PASSWORD"),
    ) as c:
        if args.cmd == "ping":
            print("reachable:", await c.ping())
            print(describe(await c.server_time()))
            return
        session = await c.login()
        if args.cmd == "login":
            print(describe(session))
        elif args.cmd == "dump":
            for title, coro in (
                ("DEVICES", c.read_devices()),
                ("SYSTEM STATUS", c.read_system_status()),
                ("ERROR COUNT", c.read_error_count()),
                ("VERSIONS", c.read_versions()),
            ):
                print(f"===== {title}")
                try:
                    print(describe(await coro, max_depth=args.depth))
                except Exception as err:  # noqa: BLE001
                    print("ERROR:", err)
        elif args.cmd == "call":
            print(describe(await c.call(args.method), max_depth=args.depth))


def _load_env_file(path: str = ".env.local") -> None:
    """Load KEY=VALUE lines (credentials for local testing, never committed)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            key, sep, value = line.strip().partition("=")
            if sep and key and not key.startswith("#") and value:
                os.environ.setdefault(key, value)


def main() -> None:
    _load_env_file()
    p = argparse.ArgumentParser(prog="pyvariovent")
    p.add_argument("--host", required=True)
    p.add_argument("--user")
    p.add_argument("--password")
    p.add_argument("--depth", type=int, default=6)
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping")
    sub.add_parser("login")
    sub.add_parser("dump")
    call = sub.add_parser("call", help="call a method that only takes the UserSession")
    call.add_argument("method")
    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)
    asyncio.run(_main(args))


if __name__ == "__main__":
    main()
