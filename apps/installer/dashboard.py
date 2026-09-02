#!/usr/bin/env python3
"""Expose a containerized Hermes dashboard while Hermes itself stays loopback-only."""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
from pathlib import Path


HERMES = Path("/opt/hermes/.venv/bin/hermes")


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while chunk := await reader.read(65536):
            writer.write(chunk)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        writer.close()
        await writer.wait_closed()


async def bridge(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter, upstream_port: int) -> None:
    try:
        upstream_reader, upstream_writer = await asyncio.open_connection("127.0.0.1", upstream_port)
    except OSError:
        client_writer.close()
        await client_writer.wait_closed()
        return
    await asyncio.gather(
        pipe(client_reader, upstream_writer),
        pipe(upstream_reader, client_writer),
    )


async def operate(listen_host: str, listen_port: int, upstream_port: int) -> int:
    if not HERMES.is_file():
        raise RuntimeError(f"Hermes executable is unavailable: {HERMES}")
    dashboard = await asyncio.create_subprocess_exec(
        str(HERMES),
        "dashboard",
        "--isolated",
        "--host",
        "127.0.0.1",
        "--port",
        str(upstream_port),
        "--no-open",
        env=os.environ.copy(),
    )
    server = await asyncio.start_server(
        lambda reader, writer: bridge(reader, writer, upstream_port),
        listen_host,
        listen_port,
    )
    try:
        return await dashboard.wait()
    finally:
        server.close()
        await server.wait_closed()
        if dashboard.returncode is None:
            dashboard.send_signal(signal.SIGTERM)
            await dashboard.wait()


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--listen-host", default="0.0.0.0")
    command.add_argument("--listen-port", type=int, default=9119)
    command.add_argument("--upstream-port", type=int, default=9120)
    return command


def main() -> int:
    args = parser().parse_args()
    return asyncio.run(operate(args.listen_host, args.listen_port, args.upstream_port))


if __name__ == "__main__":
    raise SystemExit(main())
