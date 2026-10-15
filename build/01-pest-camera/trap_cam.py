#!/usr/bin/env python3
"""GH-01 sticky-trap camera: one wake-up on the Raspberry Pi Zero 2 W.

The TPL5110 timer powers the Pi once an hour. systemd starts this script once the clock is synced (trap-cam.service).
In daylight it switches the LED ring on, takes one 12 MP photo with the focus fixed at 20 cm, switches the ring off and
uploads the photo to the farm's edge computer. Photos that could not be sent wait in OUTBOX for the next wake-up. Then
it powers the Pi off; after shutdown the gpio-poweroff overlay raises GPIO 26 (pin 37), the TPL5110's DONE, and the
timer cuts the power until the next hour.

Wiring and parts: README.md. Written for the bench build; not yet run on hardware (14 Oct 2026).
"""
import datetime
import os
import subprocess
import time
import urllib.request
from pathlib import Path

from gpiozero import DigitalOutputDevice
from libcamera import controls
from picamera2 import Picamera2

SERVER = os.environ.get("GH_SERVER", "http://gh01-edge.local:8088/trap")   # count_server.py on the Pi 5
TRAP_ID = os.environ.get("GH_TRAP", "trap-2")
LIGHT_PIN = 17                     # pin 11 -> 1 kΩ -> IRLZ44N gate
FOCUS_DIOPTRES = 1 / 0.20          # the card is 20 cm from the lens
DAY_HOURS = range(6, 19)           # photos 06:00-18:59; at night the Pi powers straight off again
OUTBOX = Path("/home/pi/outbox")


def take_photo(path):
    light = DigitalOutputDevice(LIGHT_PIN, initial_value=False)
    cam = Picamera2()
    cam.configure(cam.create_still_configuration(main={"size": (4608, 2592)}))
    cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": FOCUS_DIOPTRES})
    try:
        light.on()
        cam.start()
        time.sleep(1.5)            # let exposure settle under the ring light
        cam.capture_file(str(path))
    finally:
        cam.stop()
        light.off()
        cam.close()


def upload(path):
    req = urllib.request.Request(SERVER, data=path.read_bytes(), method="POST",
                                 headers={"Content-Type": "image/jpeg", "X-Trap": TRAP_ID, "X-Taken": path.stem.split("_")[-1]})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status == 200


def main():
    OUTBOX.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now()
    if now.hour in DAY_HOURS:
        take_photo(OUTBOX / f"{TRAP_ID}_{int(now.timestamp())}.jpg")
    for p in sorted(OUTBOX.glob("*.jpg")):           # oldest first; stop at the first failure (no Wi-Fi?)
        try:
            if not upload(p):
                break
            p.unlink()
        except OSError:
            break
    subprocess.run(["sudo", "poweroff"], check=False)


if __name__ == "__main__":
    main()
