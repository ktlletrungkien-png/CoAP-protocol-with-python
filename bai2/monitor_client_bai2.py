"""Poll a CoAP sensor and optionally save readings to CSV or JSON Lines."""
from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import sys
import time

import aiocoap

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coap_common import (  # noqa: E402
    add_client_args,
    decode_json,
    positive_int,
    positive_float,
    request_with_timeout,
    run_cli,
    uri_for,
    client_context,
    transport_tuning,
)


def checked_reading(data: dict, expected_device: str) -> tuple[float, float, str]:
    if data.get("device_id") != expected_device:
        raise ValueError(f"device_id khong khop: {data.get('device_id')!r}")
    temperature = data.get("temperature")
    humidity = data.get("humidity")
    timestamp = data.get("timestamp")
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not math.isfinite(temperature):
        raise ValueError("temperature khong phai so huu han")
    if isinstance(humidity, bool) or not isinstance(humidity, (int, float)) or not math.isfinite(humidity):
        raise ValueError("humidity khong phai so huu han")
    if not 0 <= humidity <= 100:
        raise ValueError("humidity phai trong khoang 0..100")
    if not isinstance(timestamp, str) or not timestamp:
        raise ValueError("timestamp thieu hoac khong hop le")
    return float(temperature), float(humidity), timestamp


def device_id_arg(value: str) -> str:
    import re

    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError("Device ID chi gom chu, so, dau gach ngang va gach duoi")
    return value


async def run(args: argparse.Namespace) -> None:
    uri = uri_for(args, f"/iot/lab/{args.device}/data")
    context = await client_context()
    attempted = successful = 0
    total_rtt = 0.0
    csv_file = jsonl_file = None
    csv_writer = None
    try:
        if args.csv:
            Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
            csv_file = open(args.csv, "a", newline="", encoding="utf-8")
            csv_writer = csv.DictWriter(csv_file, fieldnames=["device_id", "temperature", "humidity", "timestamp", "received_at", "rtt_ms"])
            if csv_file.tell() == 0:
                csv_writer.writeheader()
        if args.jsonl:
            Path(args.jsonl).parent.mkdir(parents=True, exist_ok=True)
            jsonl_file = open(args.jsonl, "a", encoding="utf-8")

        while args.count is None or attempted < args.count:
            attempted += 1
            request = aiocoap.Message(code=aiocoap.GET, uri=uri, transport_tuning=transport_tuning(args))
            started = time.perf_counter()
            try:
                response = await request_with_timeout(context, request, args.timeout)
                rtt_ms = (time.perf_counter() - started) * 1000
                if not response.code.is_successful():
                    raise ValueError(f"Ma phan hoi CoAP khong thanh cong: {response.code}")
                data = decode_json(response)
                temperature, humidity, sensor_timestamp = checked_reading(data, args.device)
                successful += 1
                total_rtt += rtt_ms
                received_at = datetime.now().astimezone().isoformat(timespec="seconds")
                print(f"{data['device_id']} | nhiet do {temperature:.1f} C | do am {humidity:.1f}% | nhan luc {received_at}")
                has_warning = False
                if temperature > 35:
                    print("CANH BAO: Nhiet do cao")
                    has_warning = True
                if humidity < 40:
                    print("CANH BAO: Do am thap")
                    has_warning = True
                if not has_warning:
                    print("Trang thai: Binh thuong")
                row = {
                    "device_id": data["device_id"],
                    "temperature": temperature,
                    "humidity": humidity,
                    "timestamp": sensor_timestamp,
                    "received_at": received_at,
                    "rtt_ms": round(rtt_ms, 3),
                }
                if csv_writer:
                    csv_writer.writerow(row)
                    csv_file.flush()
                if jsonl_file:
                    jsonl_file.write(json.dumps(row, ensure_ascii=False) + "\n")
                    jsonl_file.flush()
            except (TimeoutError, aiocoap.error.Error) as exc:
                print(f"GET that bai (lan {attempted}): {exc}")
            except (ValueError, json.JSONDecodeError) as exc:
                print(f"Du lieu sensor khong hop le (lan {attempted}): {exc}")

            if args.count is None or attempted < args.count:
                await asyncio.sleep(args.interval)
    finally:
        average = total_rtt / successful if successful else 0.0
        print(f"Thong ke: request da thu={attempted}, thanh cong={successful}, RTT trung binh={average:.2f} ms")
        if csv_file:
            csv_file.close()
        if jsonl_file:
            jsonl_file.close()
        await context.shutdown()

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CoAP sensor monitor bai 2")
    add_client_args(parser)
    parser.add_argument("--device", type=device_id_arg, default="sensor01", help="Sensor ID")
    parser.add_argument("--count", type=positive_int, help="So lan poll; bo trong de chay den Ctrl+C")
    parser.add_argument("--interval", type=positive_float, default=3.0, help="Khoang cach giua cac lan poll (giay)")
    parser.add_argument("--csv", help="Ghi cac mau hop le vao tep CSV")
    parser.add_argument("--jsonl", help="Ghi cac mau hop le vao tep JSON Lines")
    return parser


if __name__ == "__main__":
    raise SystemExit(run_cli(run, build_parser().parse_args()))
