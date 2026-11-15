from __future__ import annotations

import math
import unittest

from app.sensors.sense_hat import SenseHatSensor


class FakeSenseHat:
    def get_temperature(self) -> float:
        return 24.1254

    def get_humidity(self) -> float:
        return 43.8765

    def get_pressure(self) -> float:
        return 0.0

    def get_accelerometer_raw(self) -> dict[str, float]:
        return {"x": 0.01234, "y": -0.02345, "z": 0.99876}

    def get_gyroscope_raw(self) -> dict[str, float]:
        return {"x": 0.1, "y": 0.2, "z": math.inf}

    def get_compass_raw(self) -> dict[str, float]:
        return {"x": 12.3, "y": -4.5, "z": 31.2}

    def get_orientation_degrees(self) -> dict[str, float]:
        return {"pitch": 1.25, "roll": 2.5, "yaw": 180.0}


class SenseHatSensorTests(unittest.TestCase):
    def test_reads_environment_motion_and_orientation(self) -> None:
        sample = SenseHatSensor(FakeSenseHat()).read()

        self.assertEqual(sample.source, "live")
        self.assertEqual(sample.sensors.temperature_c, 24.125)
        self.assertEqual(sample.sensors.humidity_pct, 43.877)
        self.assertIsNone(sample.sensors.pressure_hpa)
        self.assertEqual(sample.sensors.acceleration_g.z, 0.9988)
        self.assertEqual(sample.sensors.gyroscope_rps.x, 0.1)
        self.assertIsNone(sample.sensors.gyroscope_rps.z)
        self.assertEqual(sample.sensors.magnetic_uT.y, -4.5)
        self.assertEqual(sample.sensors.orientation_deg.yaw, 180.0)


if __name__ == "__main__":
    unittest.main()
