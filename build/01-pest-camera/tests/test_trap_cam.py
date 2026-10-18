"""Laptop tests for trap_cam.py (18 Oct 2026): the REAL script, with a fake camera + LED pin (tests/fakes) and a real HTTP
server standing in for the farm's Pi 5. Each test is one wake-up of the trap.   python -m pytest tests -v"""
import datetime
import http.server
import importlib
import sys
import threading
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "fakes"))
sys.path.insert(0, str(HERE.parent))
import gpiozero  # noqa: E402  (the fake)
import picamera2  # noqa: E402  (the fake)


class Inbox(http.server.BaseHTTPRequestHandler):
    got = []

    def do_POST(self):
        n = int(self.headers["Content-Length"])
        Inbox.got.append((self.headers["X-Trap"], self.rfile.read(n)))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    Inbox.got = []
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Inbox)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_port}/trap"
    s.shutdown()


def wake(tmp_path, monkeypatch, url, hour):
    """One wake-up at `hour`; returns the events and whether the Pi powered off."""
    gpiozero.EVENTS.clear()
    trap = importlib.reload(importlib.import_module("trap_cam"))
    monkeypatch.setattr(trap, "OUTBOX", tmp_path)
    monkeypatch.setattr(trap, "SERVER", url)
    monkeypatch.setattr(trap.time, "sleep", lambda s: gpiozero.EVENTS.append(f"WAIT {s} s"))
    fake_now = datetime.datetime(2026, 10, 18, hour, 0)
    monkeypatch.setattr(trap.datetime, "datetime", type("D", (datetime.datetime,), {"now": staticmethod(lambda: fake_now)}))
    off = []
    monkeypatch.setattr(trap.subprocess, "run", lambda cmd, check=False: off.append(cmd))
    try:
        trap.main()
    except Exception as e:  # noqa: BLE001
        gpiozero.EVENTS.append(f"CRASH {type(e).__name__}: {e}")
    return gpiozero.EVENTS[:], bool(off)


def test_day_wake_photo_light_upload_off(tmp_path, monkeypatch, server):
    ev, off = wake(tmp_path, monkeypatch, server, hour=11)
    assert ev.index("LED ON (GPIO 17)") < ev.index("PHOTO SAVED") < ev.index("LED OFF (GPIO 17)")
    assert "FOCUS 0.20 m" in ev
    assert len(Inbox.got) == 1 and Inbox.got[0][0] == "trap-2"
    assert not list(tmp_path.glob("*.jpg")), "the outbox should be empty after a good upload"
    assert off, "the Pi must power off so the timer can cut the power"


def test_night_wake_no_photo(tmp_path, monkeypatch, server):
    ev, off = wake(tmp_path, monkeypatch, server, hour=22)
    assert not any(e.startswith(("LED", "CAMERA")) for e in ev)
    assert not Inbox.got and off


def test_wifi_down_photo_waits_in_outbox(tmp_path, monkeypatch):
    t0 = time.time()
    ev, off = wake(tmp_path, monkeypatch, "http://127.0.0.1:9/trap", hour=11)   # nothing listens on port 9
    assert len(list(tmp_path.glob("*.jpg"))) == 1 and off
    assert time.time() - t0 < 5, "a dead link must not keep the Pi awake"


def test_backlog_sent_next_hour(tmp_path, monkeypatch, server):
    (tmp_path / "trap-2_1000.jpg").write_bytes(b"old photo")
    ev, off = wake(tmp_path, monkeypatch, server, hour=12)
    assert len(Inbox.got) == 2 and Inbox.got[0][1] == b"old photo", "oldest first"
    assert not list(tmp_path.glob("*.jpg")) and off


def test_camera_crash_still_powers_off(tmp_path, monkeypatch, server):
    monkeypatch.setattr(picamera2, "FAIL_CAPTURE", True)
    ev, off = wake(tmp_path, monkeypatch, server, hour=11)
    assert ev[-1].startswith("LED OFF") or "LED OFF (GPIO 17)" in ev, "the light must go off"
    assert off, "camera error -> the Pi never powered off: it stays on and drains the battery"
