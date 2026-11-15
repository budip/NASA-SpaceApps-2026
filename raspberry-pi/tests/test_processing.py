from __future__ import annotations

import unittest

from app.models import (
    OrientationDegrees,
    SensorSample,
    SensorValues,
    Vector3,
    utc_now,
)
from app.processing import SensorProcessor


def motion_sample(
    acceleration_x: float,
    yaw: float,
    gyro_z: float = 0.01,
) -> SensorValues:
    return SensorValues(
        acceleration_g=Vector3(x=acceleration_x, y=0.0, z=1.0),
        gyroscope_rps=Vector3(x=0.0, y=0.0, z=gyro_z),
        magnetic_uT=Vector3(x=10.0, y=20.0, z=30.0),
        orientation_deg=OrientationDegrees(pitch=0.0, roll=0.0, yaw=yaw),
    )


def sample(environment_temperature: float, window: list[SensorValues]) -> SensorSample:
    return SensorSample(
        timestamp=utc_now(),
        sensors=SensorValues(
            temperature_c=environment_temperature,
            humidity_pct=40.0,
            pressure_hpa=1012.0,
            acceleration_g=window[-1].acceleration_g,
            gyroscope_rps=window[-1].gyroscope_rps,
            magnetic_uT=window[-1].magnetic_uT,
            orientation_deg=window[-1].orientation_deg,
        ),
        source="live",
        imu_window=window,
    )


class SensorProcessorTests(unittest.TestCase):
    def test_reduces_noise_but_preserves_motion_features(self) -> None:
        window = [
            motion_sample(0.08 if index % 2 else -0.08, yaw=10.0 + index)
            for index in range(20)
        ]
        processed = SensorProcessor(expected_imu_samples=20).process(
            sample(22.0, window)
        )

        self.assertAlmostEqual(processed.sensors.acceleration_g.x, 0.0, places=3)
        self.assertGreater(processed.features.motion_rms_g, 0.07)
        self.assertGreater(processed.features.orientation_change_deg, 10.0)
        self.assertEqual(processed.quality.sample_count, 20)
        self.assertEqual(processed.quality.overall_score, 1.0)
        self.assertEqual(processed.quality.flags, [])

    def test_orientation_filter_handles_zero_degree_wraparound(self) -> None:
        window = [motion_sample(0.0, yaw=359.0), motion_sample(0.0, yaw=1.0)]
        processed = SensorProcessor(expected_imu_samples=2).process(
            sample(22.0, window)
        )

        yaw = processed.sensors.orientation_deg.yaw
        self.assertTrue(yaw < 2.0 or yaw > 358.0)
        self.assertAlmostEqual(processed.features.orientation_change_deg, 1.155, places=3)

    def test_environmental_spike_is_suppressed_and_flagged(self) -> None:
        processor = SensorProcessor(expected_imu_samples=1)
        window = [motion_sample(0.0, yaw=0.0)]
        for temperature in (22.0, 22.1, 21.9, 22.0):
            processor.process(sample(temperature, window))

        processed = processor.process(sample(80.0, window))

        self.assertLess(processed.sensors.temperature_c, 23.0)
        self.assertIn(
            "spike_suppressed_temperature_c",
            processed.quality.flags,
        )

    def test_missing_imu_data_reduces_quality(self) -> None:
        empty_window = [SensorValues() for _ in range(5)]
        processed = SensorProcessor(expected_imu_samples=20).process(
            sample(22.0, empty_window)
        )

        self.assertLess(processed.quality.overall_score, 0.5)
        self.assertIn("low_imu_sample_count", processed.quality.flags)
        self.assertIn("missing_acceleration_g", processed.quality.flags)


if __name__ == "__main__":
    unittest.main()
