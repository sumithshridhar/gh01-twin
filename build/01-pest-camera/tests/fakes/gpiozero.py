"""Fake gpiozero for laptop tests: records what the script does to the LED pin."""
EVENTS = []


class DigitalOutputDevice:
    def __init__(self, pin, initial_value=False):
        self.pin = pin

    def on(self):
        EVENTS.append(f"LED ON (GPIO {self.pin})")

    def off(self):
        EVENTS.append(f"LED OFF (GPIO {self.pin})")
