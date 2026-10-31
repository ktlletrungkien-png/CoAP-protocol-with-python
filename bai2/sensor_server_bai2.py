"""CoAP sensor server for Lab 2."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import random
from pathlib import Path
import re
import sys

import aiocoap
from aiocoap import resource

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coap_common import (  # noqa: E402
    add_server_args,
    finite_float,
    json_response,
    run_cli,
    server_context,
)


def timestamp_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def device_id_arg(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError("Device ID chi gom chu, so, dau gach ngang va gach duoi")
    return value


def humidity_arg(value: str) -> float:
    number = finite_float(value)
    if not 0 <= number <= 100:
        raise argparse.ArgumentTypeError("Do am phai trong khoang 0..100")
    return number


class SensorResource(resource.Resource):
    """A sensor whose values can be fixed or refreshed randomly."""

    def __init__(self, device_id: str, temperature: float | None = None, humidity: float | None = None) -> None:
        super().__init__()
        self.device_id = device_id
        self.fixed_temperature = temperature
        self.fixed_humidity = humidity
        self.temperature = temperature if temperature is not None else round(random.uniform(25, 40), 1)
        self.humidity = humidity if humidity is not None else round(random.uniform(30, 70), 1)
        self.timestamp = timestamp_now()

    def update(self) -> None:
        if self.fixed_temperature is None:
            self.temperature = round(random.uniform(25, 40), 1)
        if self.fixed_humidity is None:
            self.humidity = round(random.uniform(30, 70), 1)
        self.timestamp = timestamp_now()

    async def render_get(self, request: aiocoap.Message) -> aiocoap.Message:
        payload = {
            "device_id": self.device_id,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "timestamp": self.timestamp,
        }
        return json_response(payload)


async def serve(args: argparse.Namespace) -> None:
    if len(set(args.devices)) != len(args.devices):
        raise ValueError("Danh sach device ID khong duoc trung lap")
    site = resource.Site()
    sensors = []
    for device_id in args.devices:
        sensor = SensorResource(device_id, args.temperature, args.humidity)
        sensors.append(sensor)
        site.add_resource(["iot", "lab", device_id, "data"], sensor)

    async def refresh_sensors() -> None:
        while True:
            await asyncio.sleep(3)
            for sensor in sensors:
                sensor.update()

    refresh_task = asyncio.create_task(refresh_sensors())
    context = None
    device_paths = ", ".join(f"/iot/lab/{device_id}/data" for device_id in args.devices)
    try:
        context = await server_context(site, args)
        print(f"CoAP Sensor Server dang lang nghe tai coap://{args.host}:{args.port} ({device_paths})", flush=True)
        await asyncio.Future()
    finally:
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass
        if context is not None:
            await context.shutdown()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CoAP sensor server bai 2")
    add_server_args(parser)
    parser.add_argument("--devices", nargs="+", type=device_id_arg, default=["sensor01"], metavar="ID", help="Danh sach sensor ID")
    parser.add_argument("--temperature", type=finite_float, help="Nhiet do co dinh de thu nghiem")
    parser.add_argument("--humidity", type=humidity_arg, help="Do am co dinh de thu nghiem (0..100)")
    return parser


if __name__ == "__main__":
    raise SystemExit(run_cli(serve, build_parser().parse_args()))
