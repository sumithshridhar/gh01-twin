"""The serial link to the Arduino Mega (r1_io.ino). Starter code, untested on hardware.

Keeps the Mega's 300 ms watchdog fed, parses its status lines, and gives the other scripts one place to send commands.
"""
import threading
import time

import serial
import yaml


class Link:
    def __init__(self, cfg):
        self.cfg = cfg
        self.ser = serial.Serial(cfg["serial_port"], 115200, timeout=0.05)
        time.sleep(2.0)                          # the Mega resets when the port opens
        self.lock = threading.Lock()
        self.pulses = [0, 0, 0, 0]
        self.estop_ok = False
        self.tank_ok = False
        self.armed = False
        self.last_status = 0.0
        self.drive = (0, 0)
        self._stop = False
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._feeder, daemon=True).start()

    def send(self, line):
        with self.lock:
            self.ser.write((line + "\n").encode())

    def _reader(self):
        buf = b""
        while not self._stop:
            buf += self.ser.read(256)
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                parts = raw.decode(errors="ignore").split()
                if len(parts) == 8 and parts[0] == "S":
                    self.pulses = [int(x) for x in parts[1:5]]
                    self.estop_ok, self.tank_ok, self.armed = parts[5] == "1", parts[6] == "1", parts[7] == "1"
                    self.last_status = time.time()

    def _feeder(self):
        while not self._stop:                    # resend the current drive command every 100 ms (watchdog food)
            left, right = self.drive
            self.send(f"D {left} {right}")
            time.sleep(0.1)

    def set_drive(self, left, right):
        self.drive = (max(-100, min(100, int(left))), max(-100, min(100, int(right))))

    def distance_m(self):
        """Mean distance of the four wheels since start (signs handle reverse)."""
        w = self.cfg["wheel"]
        per_pulse = 3.14159 * w["diameter_m"] / w["pulses_per_rev"]
        return sum(self.pulses) / 4.0 * per_pulse

    def close(self):
        self._stop = True
        self.send("D 0 0")
        self.send("E 0")


def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)
