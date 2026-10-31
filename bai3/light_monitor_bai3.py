"""Observe a CoAP device using one RFC 7641 Observe request."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import re
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import aiocoap

from coap_common import (
    add_client_args,
    client_context,
    decode_json,
    positive_float,
    positive_int,
    run_cli,
    transport_tuning,
    uri_for,
)


def _device_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError("device ID may contain only letters, digits, _ and -")
    return value


def _show(response, sequence: int, expected_device: str) -> None:
    if not response.code.is_successful():
        raise ValueError(f"server returned {response.code}")
    data = decode_json(response)
    if data.get("device_id") != expected_device:
        raise ValueError("response device_id did not match the requested device")
    if data.get("status") not in ("ON", "OFF"):
        raise ValueError("response status must be ON or OFF")
    received = datetime.now().astimezone().isoformat(timespec="seconds")
    marker = "initial" if sequence == 1 else f"update {sequence - 1}"
    print(f"[{received}] {marker}: {data.get('device_id')} = {data.get('status')} (Code: {response.code})", flush=True)


async def _run(args: argparse.Namespace) -> int:
    context = await client_context()
    request = aiocoap.Message(
        code=aiocoap.GET,
        uri=uri_for(args, f"/iot/lab/{args.device}/status"),
        observe=0,
    )
    request.transport_tuning = transport_tuning(args)
    observation = None
    try:
        pending = context.request(request)
        observation = pending.observation
        if observation is None:
            raise RuntimeError("aiocoap did not create an observation for this request")
        try:
            initial = await asyncio.wait_for(pending.response, timeout=args.timeout)
        except asyncio.TimeoutError as exc:
            pending.response.cancel()
            raise TimeoutError(f"Server khong phan hoi trong {args.timeout:g} giay") from exc
        if initial.opt.observe is None:
            raise ValueError("server did not accept the Observe request")
        _show(initial, 1, args.device)
        seen = 1
        if args.count is not None and seen >= args.count:
            return 0

        notifications = observation.__aiter__()
        while True:
            try:
                if args.idle_timeout is None:
                    update = await notifications.__anext__()
                else:
                    update = await asyncio.wait_for(notifications.__anext__(), timeout=args.idle_timeout)
            except asyncio.TimeoutError:
                print(f"No notification received for {args.idle_timeout:g} seconds; stopping.", flush=True)
                return 0
            except StopAsyncIteration:
                print("Observation ended by server.", flush=True)
                return 0
            _show(update, seen + 1, args.device)
            seen += 1
            if args.count is not None and seen >= args.count:
                return 0
    finally:
        if observation is not None and not observation.cancelled:
            observation.cancel()
        await context.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description="Observe device status notifications from the server.")
    add_client_args(parser)
    parser.add_argument("--device", type=_device_id, default="light01", help="device ID (default: light01)")
    parser.add_argument("--count", type=positive_int, help="stop after this many messages, including the initial status")
    parser.add_argument("--idle-timeout", type=positive_float, help="stop after this many seconds without a notification")
    args = parser.parse_args()
    return run_cli(_run, args)


if __name__ == "__main__":
    raise SystemExit(main())
