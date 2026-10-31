"""Observable CoAP device server for the Bai 3 lab."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import aiocoap
from aiocoap import resource

from coap_common import add_server_args, run_cli, server_context


class LightResource(resource.ObservableResource):
    """A small observable device resource with a transition journal."""

    content_format = 50  # application/json

    def __init__(self, device_id: str = "light01", log_file: str | Path | None = None):
        super().__init__()
        self.device_id = device_id
        self.status = "OFF"
        self.log_file = Path(log_file) if log_file else None
        self.logger = logging.getLogger(f"{__name__}.{device_id}")

    def _payload(self) -> bytes:
        return json.dumps(
            {
                "device_id": self.device_id,
                "status": self.status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            separators=(",", ":"),
        ).encode("utf-8")

    def _response(self, code: aiocoap.numbers.codes.Code) -> aiocoap.Message:
        return aiocoap.Message(code=code, payload=self._payload(), content_format=self.content_format)

    def _error(self, code: aiocoap.numbers.codes.Code, detail: str) -> aiocoap.Message:
        body = json.dumps({"error": detail}, separators=(",", ":")).encode("utf-8")
        return aiocoap.Message(code=code, payload=body, content_format=self.content_format)

    async def render_get(self, request: aiocoap.Message) -> aiocoap.Message:
        return self._response(aiocoap.CONTENT)

    async def render_put(self, request: aiocoap.Message) -> aiocoap.Message:
        if request.opt.content_format != self.content_format:
            return self._error(aiocoap.UNSUPPORTED_CONTENT_FORMAT, "Content-Format must be application/json (50)")
        try:
            decoded = request.payload.decode("utf-8")
            body: Any = json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._error(aiocoap.BAD_REQUEST, "payload must be valid UTF-8 JSON")
        if not isinstance(body, dict):
            return self._error(aiocoap.BAD_REQUEST, "payload must be a JSON object")
        if "device_id" not in body or "command" not in body:
            return self._error(aiocoap.BAD_REQUEST, "device_id and command are required")
        if body.get("device_id") != self.device_id:
            return self._error(aiocoap.NOT_FOUND, "device_id does not match this resource")
        command = body["command"]
        if command not in ("ON", "OFF"):
            return self._error(aiocoap.BAD_REQUEST, "command must be ON or OFF")

        changed = command != self.status
        if changed:
            try:
                self._write_transition(command)
            except OSError as exc:
                print(f"ERROR: could not write the transition journal for {self.device_id}: {exc}", file=sys.stderr, flush=True)
                return self._error(aiocoap.INTERNAL_SERVER_ERROR, "transition journal is unavailable")
            previous = self.status
            self.status = command
            print(f"{self.device_id}: {previous} -> {command}; notifying observers", flush=True)
            self.updated_state()
        return self._response(aiocoap.CHANGED)

    def _write_transition(self, command: str) -> None:
        entry = {
            "device_id": self.device_id,
            "status": command,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.logger.info("device transition: %s", entry)
        if self.log_file is not None:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.log_file.open("a", encoding="utf-8", newline="\n") as journal:
                journal.write(json.dumps(entry, separators=(",", ":")) + "\n")
        print(f"Transition: {json.dumps(entry, separators=(',', ':'))}", flush=True)

    def update_observation_count(self, newcount: int) -> None:
        self.logger.info("observer count for %s: %d", self.device_id, newcount)
        print(f"Observer count for {self.device_id}: {newcount}", flush=True)


class DeviceCollection(resource.Site):
    """A site containing one independently observable device per path."""

    def __init__(self, devices: list[str], log_file: str | None):
        super().__init__()
        for device_id in devices:
            self.add_resource(
                ["iot", "lab", device_id, "status"],
                LightResource(device_id=device_id, log_file=log_file),
            )


async def _serve(args: argparse.Namespace) -> int:
    device_ids = args.devices
    if not device_ids or any(not re.fullmatch(r"[A-Za-z0-9_-]+", name) for name in device_ids):
        raise ValueError("--devices must contain one or more IDs using letters, digits, _ or -")
    if len(set(device_ids)) != len(device_ids):
        raise ValueError("--devices must not contain duplicate names")
    site = DeviceCollection(device_ids, args.log_file)
    context = await server_context(site, args)
    print(f"CoAP server ready at coap://{args.host}:{args.port}/iot/lab/<device>/status")
    print("Devices: " + ", ".join(device_ids))
    try:
        await asyncio.Future()  # run until Ctrl+C
    finally:
        await context.shutdown()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the observable CoAP device server.")
    add_server_args(parser)
    parser.add_argument("--devices", nargs="+", default=["light01"], help="device IDs (default: light01)")
    parser.add_argument("--log-file", help="optional JSONL file for real state transitions")
    args = parser.parse_args()
    return run_cli(_serve, args)


if __name__ == "__main__":
    raise SystemExit(main())
