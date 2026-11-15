"""JSON-lines bridge for Raspberry Pi OS versions with system Sense HAT drivers.

This file intentionally uses Python 3.7-compatible syntax because Raspberry Pi
OS Buster supplies its working Sense HAT bindings through /usr/bin/python3.
"""

from __future__ import print_function

import json
import os
import sys
import threading
import time
from collections import deque

# Avoid resolving this sibling file (sense_hat.py) as the system sense_hat
# package when the bridge is executed directly by path.
_SCRIPT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
sys.path = [
    entry
    for entry in sys.path
    if os.path.abspath(entry or os.getcwd()) != _SCRIPT_DIRECTORY
]

from sense_hat import SenseHat


class SensorSampler(object):
    def __init__(self, sense):
        self.sense = sense
        self.sample_hz = max(1.0, float(os.environ.get("ASTRA_IMU_SAMPLE_HZ", "20")))
        self.period_seconds = 1.0 / self.sample_hz
        self.samples = deque(maxlen=max(4, int(self.sample_hz * 3)))
        self.environment = {}
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.last_environment_read = 0.0
        self.slow_imu_every = max(1, int(round(self.sample_hz / 5.0)))
        self.sample_number = 0
        self.slow_imu = {}
        self._sample_once()
        self.thread = threading.Thread(target=self._run, name="sense-hat-sampler")
        self.thread.daemon = True
        self.thread.start()

    @staticmethod
    def _safe_call(reader):
        try:
            return reader()
        except Exception:
            return None

    def _sample_once(self):
        started = time.monotonic()
        if self.sample_number % self.slow_imu_every == 0 or not self.slow_imu:
            self.slow_imu = {
                "magnetic_uT": self._safe_call(self.sense.get_compass_raw),
                "orientation_deg": self._safe_call(
                    self.sense.get_orientation_degrees
                ),
            }

        sample = {
            "acceleration_g": self._safe_call(self.sense.get_accelerometer_raw),
            "gyroscope_rps": self._safe_call(self.sense.get_gyroscope_raw),
            "magnetic_uT": self.slow_imu.get("magnetic_uT"),
            "orientation_deg": self.slow_imu.get("orientation_deg"),
        }
        self.sample_number += 1
        environment = None
        if started - self.last_environment_read >= 1.0:
            environment = {
                "temperature_c": self._safe_call(self.sense.get_temperature),
                "humidity_pct": self._safe_call(self.sense.get_humidity),
                "pressure_hpa": self._safe_call(self.sense.get_pressure),
            }
            self.last_environment_read = started

        with self.lock:
            self.samples.append(sample)
            if environment is not None:
                self.environment = environment

    def _run(self):
        deadline = time.monotonic()
        while not self.stop_event.is_set():
            self._sample_once()
            deadline += self.period_seconds
            delay = max(0.0, deadline - time.monotonic())
            self.stop_event.wait(delay)

    def snapshot(self):
        with self.lock:
            window = list(self.samples)
            self.samples.clear()
            environment = dict(self.environment)

        latest = window[-1] if window else {}
        payload = dict(environment)
        payload.update(latest)
        payload["imu_window"] = window
        return payload

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=2.0)


def emit(payload):
    print(json.dumps(payload, separators=(",", ":")))
    sys.stdout.flush()


def main():
    sense = SenseHat()
    sampler = SensorSampler(sense)
    emit({"ready": True})
    try:
        for command in sys.stdin:
            if command.strip() == "close":
                break
            try:
                emit({"reading": sampler.snapshot()})
            except Exception as error:
                emit({"error": type(error).__name__})
    finally:
        sampler.close()


if __name__ == "__main__":
    main()
