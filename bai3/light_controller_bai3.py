"""Interactive and batch CoAP client for controlling a Bai 3 device."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import aiocoap

from coap_common import (
    add_client_args,
    decode_json,
    request_with_timeout,
    run_cli,
    transport_tuning,
    uri_for,
    client_context,
    print_response,
)


def _device_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError("device ID may contain only letters, digits, _ and -")
    return value


async def _perform(context, args: argparse.Namespace, command: str) -> None:
    command = command.upper()
    if command == "STATUS":
        request = aiocoap.Message(code=aiocoap.GET, uri=uri_for(args, f"/iot/lab/{args.device}/status"))
    elif command in ("ON", "OFF"):
        body = json.dumps({"device_id": args.device, "command": command}, separators=(",", ":"))
        request = aiocoap.Message(
            code=aiocoap.PUT,
            uri=uri_for(args, f"/iot/lab/{args.device}/status"),
            payload=body.encode("utf-8"),
            content_format=50,
        )
    else:
        print("Enter ON, OFF, STATUS, or EXIT.")
        return

    request.transport_tuning = transport_tuning(args)
    print(f"Sending {request.code} to {request.get_request_uri()}")
    if command in ("ON", "OFF"):
        print(f"Request JSON: {request.payload.decode('utf-8')}")
    response = await request_with_timeout(context, request, args.timeout)
    print_response(response)
    if not response.code.is_successful():
        raise RuntimeError(f"{command} failed with {response.code}")
    data = decode_json(response)
    if data.get("device_id") != args.device:
        raise RuntimeError("response device_id did not match the requested device")
    status = data.get("status")
    if status not in ("ON", "OFF"):
        raise RuntimeError("response did not contain a valid ON/OFF status")
    print(f"{args.device} status: {status}")
    if command in ("ON", "OFF") and status != command:
        raise RuntimeError(f"server returned status {status} after {command}")


async def _run(args: argparse.Namespace) -> int:
    context = await client_context()
    try:
        commands = args.commands or ([args.command] if args.command else None)
        if commands is not None:
            for command in commands:
                if command.upper() == "EXIT":
                    break
                try:
                    await _perform(context, args, command)
                except (TimeoutError, aiocoap.error.Error, OSError, RuntimeError, ValueError) as exc:
                    print(f"Request failed: {exc}")
                    return 1
            return 0

        print(f"Controlling {args.device} at coap://{args.host}:{args.port}")
        while True:
            try:
                command = input("Command [ON/OFF/STATUS/EXIT]: ").strip().upper()
            except EOFError:
                print()
                break
            if command == "EXIT":
                break
            if not command:
                continue
            try:
                await _perform(context, args, command)
            except (TimeoutError, aiocoap.error.Error, OSError, RuntimeError, ValueError) as exc:
                print(f"Request failed: {exc}")
        return 0
    finally:
        await context.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description="Control an observable CoAP device.")
    add_client_args(parser)
    parser.add_argument("--device", type=_device_id, default="light01", help="device ID (default: light01)")
    parser.add_argument("--command", choices=("ON", "OFF", "STATUS", "EXIT"), help="run one command")
    parser.add_argument("--commands", nargs="+", choices=("ON", "OFF", "STATUS", "EXIT"), help="run commands in sequence")
    args = parser.parse_args()
    if args.command and args.commands:
        parser.error("use either --command or --commands, not both")
    return run_cli(_run, args)


if __name__ == "__main__":
    raise SystemExit(main())
