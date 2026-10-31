"""End-to-end CoAP checks over loopback UDP (no mocked transport)."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest

import aiocoap
from aiocoap import resource

from coap_common import server_context


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def unused_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@asynccontextmanager
async def server(module: str, *options: str):
    port = unused_udp_port()
    process = await asyncio.create_subprocess_exec(
        PYTHON, "-u", "-m", module, "--host", "127.0.0.1", "--port", str(port), *options,
        cwd=ROOT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    try:
        try:
            ready = await asyncio.wait_for(process.stdout.readline(), 5)
        except asyncio.TimeoutError:
            process.kill()
            out, err = await process.communicate()
            raise AssertionError(f"{module} did not start: {out!r} {err!r}")
        if not ready:
            out, err = await process.communicate()
            raise AssertionError(f"{module} exited during startup: {out!r} {err!r}")
        yield port, process
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), 3)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()


@asynccontextmanager
async def client():
    context = await aiocoap.Context.create_client_context(transports=["simple6"])
    try:
        yield context
    finally:
        await context.shutdown()


async def exchange(context, port: int, path: str, code, *, payload=b"", content_format=None, mtype=aiocoap.CON):
    message = aiocoap.Message(
        code=code,
        uri=f"coap://127.0.0.1:{port}{path}",
        payload=payload,
        transport_tuning=aiocoap.Reliable if mtype == aiocoap.CON else aiocoap.Unreliable,
    )
    if content_format is not None:
        message.opt.content_format = content_format
    return await asyncio.wait_for(context.request(message).response, 3)


def body(response):
    return json.loads(response.payload.decode("utf-8"))


class CoAPIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_bai1_welcome_post_latest_and_missing_resource(self):
        path = "/iot/lab/message"
        async with server("bai1.coap_server_bai1") as (port, _), client() as context:
            first = await exchange(context, port, path, aiocoap.GET)
            self.assertEqual(first.code, aiocoap.CONTENT)
            self.assertIn("Xin chao", first.payload.decode("utf-8"))

            for greeting, mtype in (("An, 123: chao", aiocoap.CON), ("Binh, 456: xin chao", aiocoap.NON)):
                posted = await exchange(context, port, path, aiocoap.POST, payload=greeting.encode(), content_format=0, mtype=mtype)
                self.assertEqual(posted.code, aiocoap.CHANGED)
                current = await exchange(context, port, path, aiocoap.GET)
                self.assertEqual(current.payload.decode(), greeting)

            bad = await exchange(context, port, path, aiocoap.POST, payload=b"  ", content_format=0)
            self.assertEqual(bad.code, aiocoap.BAD_REQUEST)
            current = await exchange(context, port, path, aiocoap.GET)
            self.assertEqual(current.payload.decode(), "Binh, 456: xin chao")

            missing = await exchange(context, port, "/iot/lab/absent", aiocoap.GET)
            self.assertEqual(missing.code, aiocoap.NOT_FOUND)

    async def test_bai2_sensor_json_multiple_devices_and_fixed_values(self):
        async with server(
            "bai2.sensor_server_bai2", "--devices", "sensor01", "sensor02",
            "--temperature", "35.1", "--humidity", "39.9",
        ) as (port, _), client() as context:
            for device in ("sensor01", "sensor02"):
                response = await exchange(context, port, f"/iot/lab/{device}/data", aiocoap.GET)
                self.assertEqual(response.code, aiocoap.CONTENT)
                self.assertEqual(response.opt.content_format, 50)
                reading = body(response)
                self.assertEqual(reading["device_id"], device)
                self.assertEqual(reading["temperature"], 35.1)
                self.assertEqual(reading["humidity"], 39.9)
                self.assertTrue(reading["timestamp"])
            missing = await exchange(context, port, "/iot/lab/sensor03/data", aiocoap.GET)
            self.assertEqual(missing.code, aiocoap.NOT_FOUND)

    async def test_bai2_refresh_happens_without_get(self):
        async with server("bai2.sensor_server_bai2", "--temperature", "30", "--humidity", "55") as (port, _), client() as context:
            path = "/iot/lab/sensor01/data"
            before = body(await exchange(context, port, path, aiocoap.GET))
            await asyncio.sleep(3.2)
            after = body(await exchange(context, port, path, aiocoap.GET))
            self.assertNotEqual(before["timestamp"], after["timestamp"])
            self.assertEqual((after["temperature"], after["humidity"]), (30, 55))

    async def test_bai2_monitor_threshold_and_log(self):
        with tempfile.TemporaryDirectory() as tempdir:
            logfile = Path(tempdir) / "samples.jsonl"
            cases = (
                ("35", "40", "Trang thai: Binh thuong"),
                ("35.1", "40", "CANH BAO: Nhiet do cao"),
                ("35", "39.9", "CANH BAO: Do am thap"),
                ("35.1", "39.9", "CANH BAO: Nhiet do cao"),
            )
            for temperature, humidity, expected in cases:
                async with server(
                    "bai2.sensor_server_bai2", "--temperature", temperature, "--humidity", humidity,
                ) as (port, _):
                    proc = await asyncio.create_subprocess_exec(
                        PYTHON, "-m", "bai2.monitor_client_bai2", "--port", str(port),
                        "--count", "1", "--jsonl", str(logfile),
                        cwd=ROOT, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                    )
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), 6)
                    self.assertEqual(proc.returncode, 0, stderr.decode(errors="replace"))
                    output = stdout.decode("utf-8")
                    self.assertIn(expected, output)
                    self.assertIn("request da thu=1", output)
            samples = [json.loads(line) for line in logfile.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(samples), 4)
            self.assertEqual([(s["temperature"], s["humidity"]) for s in samples],
                             [(35.0, 40.0), (35.1, 40.0), (35.0, 39.9), (35.1, 39.9)])
            self.assertTrue(all(s["received_at"] and s["rtt_ms"] >= 0 for s in samples))

    async def test_bai2_monitor_rejects_malformed_json_over_udp(self):
        class BadSensor(resource.Resource):
            async def render_get(self, request):
                return aiocoap.Message(code=aiocoap.CONTENT, payload=b"{broken", content_format=50)

        port = unused_udp_port()
        site = resource.Site()
        site.add_resource(["iot", "lab", "sensor01", "data"], BadSensor())
        context = await server_context(site, SimpleNamespace(host="127.0.0.1", port=port))
        try:
            monitor = await asyncio.create_subprocess_exec(
                PYTHON, "-m", "bai2.monitor_client_bai2", "--port", str(port), "--count", "1",
                cwd=ROOT, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            output, error = await asyncio.wait_for(monitor.communicate(), 4)
            self.assertEqual(monitor.returncode, 0, error.decode("utf-8", errors="replace"))
            self.assertIn("Du lieu sensor khong hop le", output.decode("utf-8"))
            self.assertIn("thanh cong=0", output.decode("utf-8"))
        finally:
            await context.shutdown()

    async def test_bai3_put_validation_observe_two_clients_and_transition_log(self):
        path = "/iot/lab/light01/status"
        with tempfile.TemporaryDirectory() as tempdir:
            journal = Path(tempdir) / "transitions.jsonl"
            async with server("bai3.light_server_bai3", "--log-file", str(journal)) as (port, _):
                async with client() as one, client() as two:
                    uri = f"coap://127.0.0.1:{port}{path}"
                    requests = [
                        context.request(aiocoap.Message(code=aiocoap.GET, uri=uri, observe=0,
                                                        transport_tuning=aiocoap.Reliable))
                        for context in (one, two)
                    ]
                    initial = await asyncio.gather(*(asyncio.wait_for(req.response, 3) for req in requests))
                    self.assertEqual([body(r)["status"] for r in initial], ["OFF", "OFF"])
                    self.assertTrue(all(r.opt.content_format == 50 for r in initial))
                    iterators = [req.observation.__aiter__() for req in requests]
                    try:
                        invalid = await exchange(one, port, path, aiocoap.PUT, payload=b'{"device_id":"light01","command":"DIM"}', content_format=50)
                        self.assertEqual(invalid.code, aiocoap.BAD_REQUEST)
                        malformed = await exchange(one, port, path, aiocoap.PUT, payload=b"{", content_format=50)
                        self.assertEqual(malformed.code, aiocoap.BAD_REQUEST)
                        nonobject = await exchange(one, port, path, aiocoap.PUT, payload=b"[]", content_format=50)
                        self.assertEqual(nonobject.code, aiocoap.BAD_REQUEST)
                        wrong_device = await exchange(one, port, path, aiocoap.PUT,
                                                      payload=b'{"device_id":"fan01","command":"ON"}', content_format=50)
                        self.assertEqual(wrong_device.code, aiocoap.NOT_FOUND)
                        wrong_format = await exchange(one, port, path, aiocoap.PUT, payload=b"{}", content_format=0)
                        self.assertEqual(wrong_format.code, aiocoap.UNSUPPORTED_CONTENT_FORMAT)

                        on_body = b'{"device_id":"light01","command":"ON"}'
                        on = await exchange(one, port, path, aiocoap.PUT, payload=on_body, content_format=50)
                        self.assertEqual(on.code, aiocoap.CHANGED)
                        on_notifications = await asyncio.gather(*(asyncio.wait_for(it.__anext__(), 3) for it in iterators))
                        self.assertEqual([body(r)["status"] for r in on_notifications], ["ON", "ON"])

                        pending = [asyncio.create_task(it.__anext__()) for it in iterators]
                        again = await exchange(one, port, path, aiocoap.PUT, payload=on_body, content_format=50, mtype=aiocoap.NON)
                        self.assertEqual(again.code, aiocoap.CHANGED)
                        await asyncio.sleep(0.35)
                        self.assertTrue(all(not task.done() for task in pending), "unchanged ON must not notify")

                        off = await exchange(one, port, path, aiocoap.PUT, payload=b'{"device_id":"light01","command":"OFF"}', content_format=50)
                        self.assertEqual(off.code, aiocoap.CHANGED)
                        off_notifications = await asyncio.gather(*(asyncio.wait_for(task, 3) for task in pending))
                        self.assertEqual([body(r)["status"] for r in off_notifications], ["OFF", "OFF"])
                    finally:
                        for req in requests:
                            req.observation.cancel()
            entries = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([entry["status"] for entry in entries], ["ON", "OFF"])
            self.assertTrue(all(entry["device_id"] == "light01" and entry["timestamp"] for entry in entries))

    async def test_bai3_optional_devices_are_independent(self):
        async with server("bai3.light_server_bai3", "--devices", "light01", "fan01", "pump01") as (port, _), client() as context:
            fan = await exchange(context, port, "/iot/lab/fan01/status", aiocoap.PUT,
                                 payload=b'{"device_id":"fan01","command":"ON"}', content_format=50)
            self.assertEqual(fan.code, aiocoap.CHANGED)
            for device, expected in (("light01", "OFF"), ("fan01", "ON"), ("pump01", "OFF")):
                response = await exchange(context, port, f"/iot/lab/{device}/status", aiocoap.GET)
                self.assertEqual(body(response)["status"], expected)

    async def test_bai3_monitor_cli_receives_observe_update(self):
        async with server("bai3.light_server_bai3") as (port, _), client() as context:
            monitor = await asyncio.create_subprocess_exec(
                PYTHON, "-u", "-m", "bai3.light_monitor_bai3", "--port", str(port),
                "--count", "2", "--idle-timeout", "2",
                cwd=ROOT, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            try:
                initial = await asyncio.wait_for(monitor.stdout.readline(), 3)
                self.assertIn(b"initial:", initial)
                self.assertIn(b"OFF", initial)
                changed = await exchange(
                    context, port, "/iot/lab/light01/status", aiocoap.PUT,
                    payload=b'{"device_id":"light01","command":"ON"}', content_format=50,
                )
                self.assertEqual(changed.code, aiocoap.CHANGED)
                remaining, error = await asyncio.wait_for(monitor.communicate(), 4)
                self.assertEqual(monitor.returncode, 0, error.decode("utf-8", errors="replace"))
                self.assertIn(b"update 1:", remaining)
                self.assertIn(b"ON", remaining)
            finally:
                if monitor.returncode is None:
                    monitor.kill()
                    await monitor.wait()

    async def test_cli_timeout_and_controller_batch(self):
        unused_port = unused_udp_port()
        timeout_process = await asyncio.create_subprocess_exec(
            PYTHON, "-m", "bai1.coap_client_bai1", "--port", str(unused_port),
            "--name", "Tester", "--student-id", "123", "--timeout", "0.3",
            cwd=ROOT, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        _, timeout_error = await asyncio.wait_for(timeout_process.communicate(), 4)
        self.assertEqual(timeout_process.returncode, 1)
        self.assertIn("Loi:", timeout_error.decode("utf-8"))

        async with server("bai3.light_server_bai3") as (port, _), client() as context:
            controller = await asyncio.create_subprocess_exec(
                PYTHON, "-m", "bai3.light_controller_bai3", "--port", str(port),
                "--commands", "STATUS", "ON", "STATUS", "OFF",
                cwd=ROOT, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            output, error = await asyncio.wait_for(controller.communicate(), 6)
            self.assertEqual(controller.returncode, 0, error.decode("utf-8", errors="replace"))
            self.assertIn("light01 status: ON", output.decode("utf-8"))
            result = await exchange(context, port, "/iot/lab/light01/status", aiocoap.GET)
            self.assertEqual(body(result)["status"], "OFF")


if __name__ == "__main__":
    unittest.main()
