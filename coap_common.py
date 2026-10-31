"""Small shared helpers for the three CoAP labs (unicast UDP)."""

import argparse
import asyncio
import ipaddress
import json
import math
import sys
from urllib.parse import quote

import aiocoap
from aiocoap import error


def positive_int(value):
    try:
        number = int(value)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("Can mot so nguyen duong") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("Gia tri phai lon hon 0")
    return number


def finite_float(value):
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("Can mot so huu han") from exc
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError("Gia tri phai huu han")
    return number


def positive_float(value):
    number = finite_float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Gia tri phai lon hon 0")
    return number


def port_number(value):
    number = positive_int(value)
    if number > 65535:
        raise argparse.ArgumentTypeError("Cong phai trong khoang 1..65535")
    return number


def host_name(value):
    value = value.strip()
    if not value or any(c in value for c in "/?#@[]") or any(c.isspace() for c in value):
        raise argparse.ArgumentTypeError("Nhap IP hoac hostname, khong kem scheme/cong")
    if ":" in value:
        try:
            ipaddress.IPv6Address(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("Dia chi IPv6 khong hop le") from exc
    return value


def add_server_args(parser):
    parser.add_argument("--host", type=host_name, default="127.0.0.1", help="IP cu the cua server")
    parser.add_argument("--port", type=port_number, default=5683, help="Cong UDP (mac dinh 5683)")


def add_client_args(parser):
    parser.add_argument("--host", type=host_name, default="127.0.0.1", help="IP/hostname cua server")
    parser.add_argument("--port", type=port_number, default=5683)
    parser.add_argument("--timeout", type=positive_float, default=5.0, help="Thoi gian cho phan hoi (giay)")
    parser.add_argument("--mtype", choices=("CON", "NON"), default="CON", help="Loai ban tin CoAP")


def uri_for(args, path):
    host = f"[{args.host}]" if ":" in args.host else args.host
    path = quote("/" + path.lstrip("/"), safe="/")
    return f"coap://{host}:{args.port}{path}"


def message_type(args):
    return aiocoap.CON if args.mtype == "CON" else aiocoap.NON


def transport_tuning(args):
    """Choose CON/NON using the public aiocoap 0.4.17 transport API."""
    return aiocoap.Reliable if args.mtype == "CON" else aiocoap.Unreliable


async def client_context():
    # Explicit UDP backends also work on Windows without optional dependencies.
    return await aiocoap.Context.create_client_context(transports=["simple6"])


async def server_context(site, args):
    if args.host in {"0.0.0.0", "::"}:
        raise ValueError("--host can IP cu the, vi du 127.0.0.1 hoac IP LAN cua may")
    return await aiocoap.Context.create_server_context(
        site, bind=(args.host, args.port), transports=["simplesocketserver"]
    )


async def request_with_timeout(context, message, timeout):
    request = context.request(message)
    try:
        return await asyncio.wait_for(request.response, timeout)
    except asyncio.TimeoutError as exc:
        request.response.cancel()
        raise TimeoutError(f"Server khong phan hoi trong {timeout:g} giay") from exc
    finally:
        if request.observation is not None and not request.observation.cancelled:
            request.observation.cancel()


def json_response(data, code=aiocoap.CONTENT):
    return aiocoap.Message(
        code=code,
        payload=json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8"),
        content_format=50,
    )


def decode_json(response):
    if response.opt.content_format != 50:
        raise ValueError("Content-Format phai la application/json (50)")
    try:
        data = json.loads(response.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Payload khong phai JSON UTF-8 hop le") from exc
    if not isinstance(data, dict):
        raise ValueError("Payload JSON phai la object")
    return data


def print_response(response):
    print(f"Code: {response.code}")
    print(f"Payload: {response.payload.decode('utf-8', errors='replace')}")


def run_cli(async_function, args):
    try:
        result = asyncio.run(async_function(args))
        return result if isinstance(result, int) else 0
    except KeyboardInterrupt:
        print("\nDa dung chuong trinh.")
        return 0
    except (OSError, ValueError, RuntimeError, TimeoutError, error.Error) as exc:
        print(f"Loi: {exc}", file=sys.stderr)
        return 1
