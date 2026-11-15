from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.analysis import BaselineAnalyzer
from app.models import SensorSample, SensorValues
from app.sensors.simulated import SimulatedSensor


def sample(temperature: float | None, humidity: float | None = 40.0) -> SensorSample:
    return SensorSample(
        timestamp=datetime.now(timezone.utc),
        sensors=SensorValues(
            temperature_c=temperature,
            humidity_pct=humidity,
            pressure_hpa=1012.0,
        ),
        source="simulated",
    )


class BaselineAnalyzerTests(unittest.TestCase):
    def test_learns_then_reports_normal(self) -> None:
        analyzer = BaselineAnalyzer(minimum_samples=3, confirmation_samples=1)

        self.assertEqual(analyzer.evaluate(sample(22.0)).status, "LEARNING")
        self.assertEqual(analyzer.evaluate(sample(22.1)).status, "LEARNING")
        self.assertEqual(analyzer.evaluate(sample(21.9)).status, "LEARNING")
        self.assertEqual(analyzer.evaluate(sample(22.0)).status, "NORMAL")

    def test_requires_consecutive_anomalies(self) -> None:
        analyzer = BaselineAnalyzer(minimum_samples=3, confirmation_samples=2)
        for temperature in (22.0, 22.1, 21.9):
            analyzer.evaluate(sample(temperature))
        analyzer.evaluate(sample(22.0))

        first = analyzer.evaluate(sample(26.0))
        second = analyzer.evaluate(sample(26.0))

        self.assertEqual(first.status, "NORMAL")
        self.assertEqual(second.status, "ALERT")
        self.assertIn("temperature", second.summary)

    def test_missing_readings_are_controlled(self) -> None:
        analyzer = BaselineAnalyzer(minimum_samples=2, confirmation_samples=1)
        analyzer.evaluate(sample(22.0))
        analyzer.evaluate(sample(22.0))
        missing = SensorSample(
            timestamp=datetime.now(timezone.utc),
            sensors=SensorValues(),
            source="live",
        )

        result = analyzer.evaluate(missing)

        self.assertEqual(result.status, "CAUTION")
        self.assertIn("unavailable", result.summary)

    def test_cycle_profile_produces_a_labeled_alert(self) -> None:
        analyzer = BaselineAnalyzer()
        sensor = SimulatedSensor("cycle")

        results = [analyzer.evaluate(sensor.read()) for _ in range(40)]

        self.assertIn("ALERT", [result.status for result in results])
        self.assertTrue(all(result.source == "simulated" for result in results))

    def test_restored_baseline_skips_learning(self) -> None:
        analyzer = BaselineAnalyzer(minimum_samples=3, confirmation_samples=1)

        restored = analyzer.restore(
            [
                SensorValues(temperature_c=22.0, humidity_pct=40.0),
                SensorValues(temperature_c=22.1, humidity_pct=40.1),
                SensorValues(temperature_c=21.9, humidity_pct=39.9),
            ]
        )
        result = analyzer.evaluate(sample(22.0))

        self.assertEqual(restored, 3)
        self.assertEqual(result.status, "NORMAL")


if __name__ == "__main__":
    unittest.main()
