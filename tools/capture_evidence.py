"""Run all seven lab programs over real local UDP and save their output.

Run from the project root: .venv/Scripts/python.exe tools/capture_evidence.py
Only synthetic student details are used. No external server is contacted.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import threading
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def invoke(script, args, name, expected=0, stdin=None):
    command = [sys.executable, "-u", script, *map(str, args)]
    result = subprocess.run(command, cwd=ROOT, env=ENV, input=stdin,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            encoding="utf-8", timeout=25)
    (OUT / name).write_text(
        f"Command: python {' '.join(command[2:])}\nExit code: {result.returncode}\n\n{result.stdout}",
        encoding="utf-8",
    )
    if result.returncode != expected:
        raise AssertionError(f"{name}: exit {result.returncode}, expected {expected}\n{result.stdout}")
    return result.stdout


class Background:
    def __init__(self, script, args, name):
        self.lines = []
        self.changed = threading.Condition()
        self.path = OUT / name
        self.file = self.path.open("w", encoding="utf-8")
        command = [sys.executable, "-u", script, *map(str, args)]
        self.file.write(f"Command: python {' '.join(command[2:])}\n\n")
        self.file.flush()
        self.process = subprocess.Popen(command, cwd=ROOT, env=ENV,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, encoding="utf-8")
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        for line in self.process.stdout:
            with self.changed:
                self.lines.append(line)
                self.file.write(line)
                self.file.flush()
                self.changed.notify_all()

    def wait_text(self, text, timeout=10):
        with self.changed:
            found = self.changed.wait_for(lambda: any(text in line for line in self.lines), timeout)
        if not found:
            raise AssertionError(f"{self.path.name}: missing {text!r}: {''.join(self.lines)}")

    def finish(self):
        code = self.process.wait(timeout=12)
        self.thread.join(timeout=2)
        if code:
            raise AssertionError(f"{self.path.name}: exit {code}: {''.join(self.lines)}")

    def close(self):
        # Windows termination is used only for the demo's endless servers.
        # Client processes complete their requests and close their own contexts.
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)
        self.thread.join(timeout=2)
        self.process.stdout.close()
        self.file.close()


def main():
    OUT.mkdir(exist_ok=True)
    from importlib.metadata import version
    metadata = {
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "python": platform.python_version(), "platform": platform.platform(),
        "aiocoap": version("aiocoap"), "transport": "real UDP, 127.0.0.1, temporary ports",
        "student_data": "Examples only: Nguyen Van A / B23DCCN001",
    }
    (OUT / "environment.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    identity = ["--name", "Nguyen Van A", "--student-id", "B23DCCN001"]
    port = free_port()
    server = Background("bai1/coap_server_bai1.py", ["--port", port], "bai1_server.txt")
    try:
        server.wait_text("dang lang nghe")
        out = invoke("bai1/coap_client_bai1.py", ["--port", port, *identity, "--count", 2, "--verify-get"], "bai1_client.txt")
        assert out.count("2.04 Changed") == 2 and "2.05 Content" in out
        out = invoke("bai1/coap_client_bai1.py", ["--port", port, *identity, "--path", "/iot/lab/missing"], "bai1_missing.txt", expected=1)
        assert "4.04 Not Found" in out
    finally:
        server.close()
    # A UDP socket that deliberately never responds guarantees the timeout path.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as silent:
        silent.bind(("127.0.0.1", 0))
        invoke("bai1/coap_client_bai1.py", ["--port", silent.getsockname()[1], *identity, "--timeout", 0.3], "bai1_timeout.txt", expected=1)

    port = free_port()
    server = Background("bai2/sensor_server_bai2.py", ["--port", port, "--devices", "sensor01", "sensor02", "sensor03", "--temperature", 36.1, "--humidity", 38.7], "bai2_server.txt")
    try:
        server.wait_text("dang lang nghe")
        out = invoke("bai2/monitor_client_bai2.py", ["--port", port, "--count", 3, "--csv", "evidence/sensor.csv", "--jsonl", "evidence/sensor.jsonl"], "bai2_monitor_alerts.txt")
        assert out.count("CANH BAO: Nhiet do cao") == 3
        assert out.count("CANH BAO: Do am thap") == 3
        invoke("bai2/monitor_client_bai2.py", ["--port", port, "--device", "sensor02", "--count", 1, "--mtype", "NON"], "bai2_sensor02_non.txt")
    finally:
        server.close()
    port = free_port()
    server = Background("bai2/sensor_server_bai2.py", ["--port", port, "--temperature", 35, "--humidity", 40], "bai2_boundary_server.txt")
    try:
        server.wait_text("dang lang nghe")
        out = invoke("bai2/monitor_client_bai2.py", ["--port", port, "--count", 1], "bai2_boundary.txt")
        assert "Trang thai: Binh thuong" in out and "CANH BAO:" not in out
    finally:
        server.close()

    port = free_port()
    server = Background("bai3/light_server_bai3.py", ["--port", port, "--devices", "light01", "fan01", "pump01", "--log-file", "evidence/transitions.jsonl"], "bai3_server.txt")
    observers = []
    try:
        server.wait_text("Devices:")
        for number in (1, 2):
            monitor = Background("bai3/light_monitor_bai3.py", ["--port", port, "--count", 3, "--idle-timeout", 8], f"bai3_observer{number}.txt")
            observers.append(monitor)
            monitor.wait_text("OFF")
        invoke("bai3/light_controller_bai3.py", ["--port", port], "bai3_controller_on.txt", stdin="WRONG\nON\nSTATUS\nEXIT\n")
        for monitor in observers:
            monitor.wait_text("ON")
        invoke("bai3/light_controller_bai3.py", ["--port", port, "--command", "ON"], "bai3_repeated_on.txt")
        invoke("bai3/light_controller_bai3.py", ["--port", port, "--commands", "STATUS", "OFF", "STATUS", "--mtype", "NON"], "bai3_controller_non.txt")
        for monitor in observers:
            monitor.finish()
            text = "".join(monitor.lines)
            assert text.count("Status: ON") == 1 or text.count(" = ON ") == 1
        invoke("bai3/light_controller_bai3.py", ["--port", port, "--device", "fan01", "--commands", "ON", "STATUS", "OFF"], "bai3_fan01.txt")
        invoke("bai3/light_controller_bai3.py", ["--port", port, "--device", "pump01", "--commands", "ON", "STATUS", "OFF"], "bai3_pump01.txt")
    finally:
        for monitor in observers:
            monitor.close()
        server.close()
    print("Captured real CLI evidence for all seven programs in evidence/.")


if __name__ == "__main__":
    # These are the only append-mode outputs overwritten by a repeat capture.
    for filename in ("sensor.csv", "sensor.jsonl", "transitions.jsonl"):
        path = OUT / filename
        if path.exists():
            path.unlink()
    main()
