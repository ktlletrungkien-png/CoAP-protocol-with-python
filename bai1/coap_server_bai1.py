"""CoAP message resource for Lab 1."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys

import aiocoap
from aiocoap import resource

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coap_common import add_server_args, run_cli, server_context  # noqa: E402


class MessageResource(resource.Resource):
    """Serve a welcome message until a client posts a newer message."""

    def __init__(self) -> None:
        super().__init__()
        self.latest_message: str | None = None

    async def render_get(self, request: aiocoap.Message) -> aiocoap.Message:
        body = self.latest_message or "Xin chao tu CoAP Server"
        requested_path = "/" + "/".join(request.opt.uri_path or ())
        requested_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        print(f"[{requested_at}] GET {requested_path}", flush=True)
        return aiocoap.Message(code=aiocoap.CONTENT, payload=body.encode("utf-8"), content_format=0)

    async def render_post(self, request: aiocoap.Message) -> aiocoap.Message:
        try:
            message = request.payload.decode("utf-8").strip()
        except UnicodeDecodeError:
            return aiocoap.Message(code=aiocoap.BAD_REQUEST, payload=b"Payload phai la UTF-8")
        if not message:
            return aiocoap.Message(code=aiocoap.BAD_REQUEST, payload=b"Thong diep khong duoc de trong")

        self.latest_message = message
        received_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        print(f"[{received_at}] Nhan thong diep: {message}", flush=True)
        return aiocoap.Message(
            code=aiocoap.CHANGED,
            payload="Server da nhan thong diep".encode("utf-8"),
            content_format=0,
        )


async def serve(args: argparse.Namespace) -> None:
    site = resource.Site()
    site.add_resource(["iot", "lab", "message"], MessageResource())
    context = await server_context(site, args)
    print(f"CoAP Server bai1 dang lang nghe tai coap://{args.host}:{args.port}/iot/lab/message", flush=True)
    try:
        await asyncio.Future()
    finally:
        await context.shutdown()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CoAP server bai 1: resource message")
    add_server_args(parser)
    return parser


if __name__ == "__main__":
    raise SystemExit(run_cli(serve, build_parser().parse_args()))
