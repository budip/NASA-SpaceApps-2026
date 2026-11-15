from __future__ import annotations

import math
import json
import os
import select
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.models import (
    OrientationDegrees,
    SensorSample,
    SensorValues,
    SourceName,
    Vector3,
    utc_now,
)


def _safe_read(
    reader: Callable[[], float],
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    try:
        value = float(reader())
    except (OSError, RuntimeError, TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    if minimum is not None and value < minimum:
        return None
    if maximum is not None and value > maximum:
        return None
    return round(value, 3)


def _safe_mapping(reader: Callable[[], dict[str, float]]) -> dict[str, float] | None:
    try:
        raw = reader()
    except (OSError, RuntimeError, TypeError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None

    values: dict[str, float] = {}
    for field, raw_value in raw.items():
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            values[field] = round(value, 4)
    return values or None


def _safe_vector(reader: Callable[[], dict[str, float]]) -> Vector3 | None:
    values = _safe_mapping(reader)
    if values is None:
        return None
    vector = Vector3(**{field: values.get(field) for field in ("x", "y", "z")})
    return vector if any(value is not None for value in vector.model_dump().values()) else None


def _safe_orientation(
    reader: Callable[[], dict[str, float]],
) -> OrientationDegrees | None:
    values = _safe_mapping(reader)
    if values is None:
        return None
    orientation = OrientationDegrees(
        **{field: values.get(field) for field in ("pitch", "roll", "yaw")}
    )
    return (
        orientation
        if any(value is not None for value in orientation.model_dump().values())
        else None
    )


class SenseHatSensor:
    source: SourceName = "live"

    def __init__(self, sense: Any | None = None) -> None:
        self._bridge: _SenseHatBridge | None = None
        bridge_python = os.environ.get("ASTRA_SENSE_HAT_PYTHON")
        if sense is None and bridge_python:
            self._bridge = _SenseHatBridge(bridge_python)
        elif sense is None:
            try:
                from sense_hat import SenseHat
                sense = SenseHat()
            except (ImportError, OSError):
                self._bridge = _SenseHatBridge()
        self._sense = sense

    def read(self) -> SensorSample:
        if self._bridge is not None:
            readings = self._bridge.read()
            return self._sample_from_mapping(readings)

        return SensorSample(
            timestamp=utc_now(),
            sensors=SensorValues(
                temperature_c=_safe_read(
                    self._sense.get_temperature,
                    minimum=-40.0,
                    maximum=120.0,
                ),
                humidity_pct=_safe_read(
                    self._sense.get_humidity,
                    minimum=0.0,
                    maximum=100.0,
                ),
                pressure_hpa=_safe_read(
                    self._sense.get_pressure,
                    minimum=100.0,
                    maximum=1200.0,
                ),
                acceleration_g=_safe_vector(self._sense.get_accelerometer_raw),
                gyroscope_rps=_safe_vector(self._sense.get_gyroscope_raw),
                magnetic_uT=_safe_vector(self._sense.get_compass_raw),
                orientation_deg=_safe_orientation(
                    self._sense.get_orientation_degrees
                ),
            ),
            source="live",
        )

    def close(self) -> None:
        if self._bridge is not None:
            self._bridge.close()

    @staticmethod
    def _sample_from_mapping(readings: dict[str, Any]) -> SensorSample:
        raw_window = readings.get("imu_window")
        imu_window = [
            SenseHatSensor._motion_from_mapping(item)
            for item in raw_window
            if isinstance(item, dict)
        ] if isinstance(raw_window, list) else []
        return SensorSample(
            timestamp=utc_now(),
            sensors=SensorValues(
                temperature_c=_safe_read(
                    lambda: readings.get("temperature_c"),
                    minimum=-40.0,
                    maximum=120.0,
                ),
                humidity_pct=_safe_read(
                    lambda: readings.get("humidity_pct"),
                    minimum=0.0,
                    maximum=100.0,
                ),
                pressure_hpa=_safe_read(
                    lambda: readings.get("pressure_hpa"),
                    minimum=100.0,
                    maximum=1200.0,
                ),
                acceleration_g=_safe_vector(
                    lambda: readings.get("acceleration_g")
                ),
                gyroscope_rps=_safe_vector(
                    lambda: readings.get("gyroscope_rps")
                ),
                magnetic_uT=_safe_vector(lambda: readings.get("magnetic_uT")),
                orientation_deg=_safe_orientation(
                    lambda: readings.get("orientation_deg")
                ),
            ),
            source="live",
            imu_window=imu_window,
        )

    @staticmethod
    def _motion_from_mapping(readings: dict[str, Any]) -> SensorValues:
        return SensorValues(
            acceleration_g=_safe_vector(
                lambda: readings.get("acceleration_g")
            ),
            gyroscope_rps=_safe_vector(lambda: readings.get("gyroscope_rps")),
            magnetic_uT=_safe_vector(lambda: readings.get("magnetic_uT")),
            orientation_deg=_safe_orientation(
                lambda: readings.get("orientation_deg")
            ),
        )


class _SenseHatBridge:
    def __init__(self, bridge_python: str = "/usr/bin/python3") -> None:
        bridge_script = Path(__file__).with_name("sense_hat_bridge.py")
        self._process = subprocess.Popen(
            [bridge_python, str(bridge_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        ready = self._read_message(timeout_seconds=60.0)
        if ready.get("ready") is not True:
            self.close()
            raise RuntimeError("Sense HAT bridge failed to initialize")

    def read(self) -> dict[str, Any]:
        if self._process.stdin is None:
            raise RuntimeError("Sense HAT bridge input is unavailable")
        self._process.stdin.write("read\n")
        self._process.stdin.flush()
        message = self._read_message(timeout_seconds=15.0)
        reading = message.get("reading")
        if not isinstance(reading, dict):
            error_name = message.get("error", "unknown error")
            raise RuntimeError(f"Sense HAT bridge read failed: {error_name}")
        return reading

    def close(self) -> None:
        process = self._process
        if process.poll() is not None:
            return
        if process.stdin is not None:
            try:
                process.stdin.write("close\n")
                process.stdin.flush()
            except BrokenPipeError:
                pass
        try:
            process.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            process.terminate()

    def _read_message(self, timeout_seconds: float) -> dict[str, Any]:
        if self._process.stdout is None:
            raise RuntimeError("Sense HAT bridge output is unavailable")
        ready, _, _ = select.select(
            [self._process.stdout],
            [],
            [],
            timeout_seconds,
        )
        if not ready:
            self.close()
            raise RuntimeError("Sense HAT bridge timed out")
        line = self._process.stdout.readline()
        if not line:
            raise RuntimeError("Sense HAT bridge stopped unexpectedly")
        try:
            message = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError("Sense HAT bridge returned invalid JSON") from error
        if not isinstance(message, dict):
            raise RuntimeError("Sense HAT bridge returned an invalid message")
        return message
