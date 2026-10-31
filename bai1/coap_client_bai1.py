"""CoAP GET/POST client for Lab 1."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

import aiocoap

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coap_common import (  # noqa: E402
    add_client_args,
    positive_int,
    print_response,
    request_with_timeout,
    run_cli,
    uri_for,
    client_context,
    transport_tuning,
)


def nonblank(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("Gia tri khong duoc de trong")
    return value


async def run(args: argparse.Namespace) -> int:
    context = await client_context()
    try:
        uri = uri_for(args, args.path)
        get_request = aiocoap.Message(code=aiocoap.GET, uri=uri, transport_tuning=transport_tuning(args))
        print("GET thong diep hien tai:")
        response = await request_with_timeout(context, get_request, args.timeout)
        print_response(response)
        if response.code.class_ == 4:
            return 1

        greeting = f"{args.message} - {args.student_id} - {args.name}"
        for index in range(args.count):
            request = aiocoap.Message(
                code=aiocoap.POST,
                uri=uri,
                payload=greeting.encode("utf-8"),
                content_format=0,
                transport_tuning=transport_tuning(args),
            )
            print(f"POST thong diep ({index + 1}/{args.count}):")
            print(f"URI: {uri}")
            print(f"Payload: {greeting}")
            response = await request_with_timeout(context, request, args.timeout)
            print_response(response)
            if response.code.class_ == 4:
                return 1

        if args.verify_get:
            print("GET xac minh thong diep moi nhat:")
            request = aiocoap.Message(code=aiocoap.GET, uri=uri, transport_tuning=transport_tuning(args))
            response = await request_with_timeout(context, request, args.timeout)
            print_response(response)
            if response.code.class_ == 4:
                return 1
    finally:
        await context.shutdown()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CoAP client bai 1: GET va POST message")
    add_client_args(parser)
    parser.add_argument("--name", required=True, type=nonblank, help="Ho ten sinh vien")
    parser.add_argument("--student-id", required=True, type=nonblank, help="Ma so sinh vien")
    parser.add_argument("--message", default="Xin chao tu CoAP Client", type=nonblank, help="Noi dung loi chao")
    parser.add_argument("--count", type=positive_int, default=1, help="So lan POST")
    parser.add_argument("--verify-get", action="store_true", help="GET lai de xac minh thong diep moi nhat")
    parser.add_argument("--path", default="/iot/lab/message", help="URI path (co the dung de demo 4.04)")
    return parser


if __name__ == "__main__":
    raise SystemExit(run_cli(run, build_parser().parse_args()))
