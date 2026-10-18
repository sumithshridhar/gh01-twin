"""Fake picamera2 for laptop tests: records the camera steps; FAIL_CAPTURE makes the capture raise like a loose ribbon."""
from gpiozero import EVENTS

FAIL_CAPTURE = False


class Picamera2:
    def create_still_configuration(self, main):
        return main

    def configure(self, cfg):
        EVENTS.append(f"CAMERA {cfg['size'][0]}x{cfg['size'][1]}")

    def set_controls(self, c):
        EVENTS.append(f"FOCUS {1 / c['LensPosition']:.2f} m")

    def start(self):
        EVENTS.append("CAMERA START")

    def capture_file(self, path):
        if FAIL_CAPTURE:
            raise RuntimeError("Camera frontend has timed out!")
        with open(path, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0 fake jpeg \xff\xd9")
        EVENTS.append("PHOTO SAVED")

    def stop(self):
        EVENTS.append("CAMERA STOP")

    def close(self):
        pass
