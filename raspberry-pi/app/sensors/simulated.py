from __future__ import annotations

import math

from app.models import (
    OrientationDegrees,
    SensorSample,
    SensorValues,
    SourceName,
    Vector3,
    utc_now,
)


class SimulatedSensor:
    """Deterministic room-like data for development and rehearsals."""

    source: SourceName = "simulated"

    def __init__(self, profile: str = "cycle", imu_sample_hz: int = 20) -> None:
        self.profile = profile
        self.imu_sample_hz = max(1, imu_sample_hz)
        self._sample_number = 0

    def read(self) -> SensorSample:
        index = self._sample_number
        self._sample_number += 1

        temperature = 22.4 + math.sin(index / 4.0) * 0.08
        humidity = 41.0 + math.sin(index / 5.0) * 0.18
        pressure = 1012.7 + math.sin(index / 6.0) * 0.10

        # Leave enough time for the default 20-sample baseline, then create a
        # repeatable, obviously simulated event for six samples every minute.
        if self.profile == "cycle" and 30 <= index % 60 < 36:
            temperature += 3.5
            humidity += 9.0

        imu_window = [
            self._motion_sample(index, sub_sample)
            for sub_sample in range(self.imu_sample_hz)
        ]
        latest_motion = imu_window[-1]

        return SensorSample(
            timestamp=utc_now(),
            sensors=SensorValues(
                temperature_c=round(temperature, 3),
                humidity_pct=round(humidity, 3),
                pressure_hpa=round(pressure, 3),
                acceleration_g=latest_motion.acceleration_g,
                gyroscope_rps=latest_motion.gyroscope_rps,
                magnetic_uT=latest_motion.magnetic_uT,
                orientation_deg=latest_motion.orientation_deg,
            ),
            source="simulated",
            imu_window=imu_window,
        )

    def _motion_sample(self, index: int, sub_sample: int) -> SensorValues:
        phase = index + sub_sample / self.imu_sample_hz
        jitter = math.sin((index * self.imu_sample_hz + sub_sample) * 1.7)
        return SensorValues(
            acceleration_g=Vector3(
                x=round(math.sin(phase / 8.0) * 0.02 + jitter * 0.003, 4),
                y=round(math.cos(phase / 9.0) * 0.02 - jitter * 0.002, 4),
                z=round(1.0 + math.sin(phase / 10.0) * 0.01 + jitter * 0.002, 4),
            ),
            gyroscope_rps=Vector3(
                x=round(math.sin(phase / 7.0) * 0.015 + jitter * 0.001, 4),
                y=round(math.cos(phase / 8.0) * 0.015 - jitter * 0.001, 4),
                z=round(math.sin(phase / 9.0) * 0.01, 4),
            ),
            magnetic_uT=Vector3(
                x=round(18.0 + math.sin(phase / 12.0) + jitter * 0.1, 4),
                y=round(-7.0 + math.cos(phase / 13.0) - jitter * 0.1, 4),
                z=round(35.0 + math.sin(phase / 14.0), 4),
            ),
            orientation_deg=OrientationDegrees(
                pitch=round((2.0 + math.sin(phase / 10.0)) % 360.0, 4),
                roll=round((1.0 + math.cos(phase / 11.0)) % 360.0, 4),
                yaw=round((180.0 + phase * 0.5) % 360.0, 4),
            ),
        )
