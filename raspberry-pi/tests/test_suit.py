from __future__ import annotations

import unittest

from app.main import create_app
from app.suit import (
    DisabledSuitTelemetry,
    SimulatedSuitTelemetry,
    pressure_status,
    temperature_status,
)


class SuitTelemetryTests(unittest.TestCase):
    def test_pressure_threshold_boundaries(self) -> None:
        self.assertEqual(pressure_status(None), "UNAVAILABLE")
        self.assertEqual(pressure_status(248.0), "CRITICAL_LOW")
        self.assertEqual(pressure_status(248.1), "WARN_LOW")
        self.assertEqual(pressure_status(276.0), "WARN_LOW")
        self.assertEqual(pressure_status(276.1), "NOMINAL")
        self.assertEqual(pressure_status(296.0), "NOMINAL")
        self.assertEqual(pressure_status(365.0), "WARN_HIGH")
        self.assertEqual(pressure_status(455.0), "CRITICAL_HIGH")

    def test_temperature_threshold_boundaries(self) -> None:
        self.assertEqual(temperature_status(None), "UNAVAILABLE")
        self.assertEqual(temperature_status(9.9), "CRITICAL_LOW")
        self.assertEqual(temperature_status(10.0), "WARN_LOW")
        self.assertEqual(temperature_status(19.9), "WARN_LOW")
        self.assertEqual(temperature_status(20.0), "COMFORT")
        self.assertEqual(temperature_status(30.0), "COMFORT")
        self.assertEqual(temperature_status(30.1), "WARN_HIGH")
        self.assertEqual(temperature_status(43.0), "WARN_HIGH")
        self.assertEqual(temperature_status(43.1), "CRITICAL_HIGH")

    def test_simulated_values_are_bounded_and_truthfully_labeled(self) -> None:
        source = SimulatedSuitTelemetry(seed=7)

        readings = [source.read() for _ in range(100)]

        self.assertTrue(
            all(286.0 <= pressure.pressure_hpa <= 306.0 for pressure, _ in readings)
        )
        self.assertTrue(
            all(22.0 <= temperature.temperature_c <= 27.0 for _, temperature in readings)
        )
        self.assertTrue(all(pressure.source == "simulated" for pressure, _ in readings))
        self.assertTrue(
            all(temperature.source == "simulated" for _, temperature in readings)
        )
        self.assertTrue(
            all(
                "sense_hat_pressure_is_ambient_not_suit_pressure" in pressure.flags
                for pressure, _ in readings
            )
        )

    def test_disabled_source_never_invents_values(self) -> None:
        pressure, temperature = DisabledSuitTelemetry().read()

        self.assertIsNone(pressure.pressure_hpa)
        self.assertIsNone(temperature.temperature_c)
        self.assertEqual(pressure.status, "UNAVAILABLE")
        self.assertEqual(temperature.status, "UNAVAILABLE")

    def test_openapi_exposes_additive_suit_fields(self) -> None:
        properties = create_app().openapi()["components"]["schemas"][
            "StatusResponse"
        ]["properties"]

        self.assertIn("suit_pressure", properties)
        self.assertIn("suit_temperature", properties)


if __name__ == "__main__":
    unittest.main()
