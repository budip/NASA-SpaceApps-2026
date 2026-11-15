from __future__ import annotations

import unittest

from app.biometrics import DisabledBiometrics, SimulatedBiometrics


class BiometricsTests(unittest.TestCase):
    def test_simulated_values_are_bounded_and_labeled(self) -> None:
        source = SimulatedBiometrics(seed=7)

        readings = [source.read() for _ in range(100)]

        self.assertTrue(all(reading.source == "simulated" for reading in readings))
        self.assertTrue(
            all(
                "simulated_biometrics" in reading.quality.flags
                for reading in readings
            )
        )
        self.assertTrue(
            all(58.0 <= reading.heart_rate_bpm <= 96.0 for reading in readings)
        )
        self.assertTrue(
            all(
                96.0 <= reading.oxygen_saturation_pct <= 99.5
                for reading in readings
            )
        )
        self.assertTrue(
            all(
                36.3 <= reading.body_temperature_c <= 37.3
                for reading in readings
            )
        )
        self.assertTrue(
            all(
                reading.blood_pressure.systolic_mm_hg
                > reading.blood_pressure.diastolic_mm_hg
                for reading in readings
            )
        )

    def test_seed_makes_demo_sequence_repeatable(self) -> None:
        first = SimulatedBiometrics(seed=42)
        second = SimulatedBiometrics(seed=42)

        first_values = [first.read().model_dump(exclude={"timestamp"}) for _ in range(5)]
        second_values = [
            second.read().model_dump(exclude={"timestamp"}) for _ in range(5)
        ]

        self.assertEqual(first_values, second_values)

    def test_disabled_source_never_invents_values(self) -> None:
        reading = DisabledBiometrics().read()

        self.assertEqual(reading.source, "unavailable")
        self.assertIsNone(reading.heart_rate_bpm)
        self.assertIn("biometrics_disabled", reading.quality.flags)

    def test_heart_rate_threshold_uses_140_bpm_critical_limit(self) -> None:
        self.assertEqual(SimulatedBiometrics.heart_rate_status(None), "UNAVAILABLE")
        self.assertEqual(SimulatedBiometrics.heart_rate_status(119.9), "NOMINAL")
        self.assertEqual(SimulatedBiometrics.heart_rate_status(120.0), "WARN_HIGH")
        self.assertEqual(SimulatedBiometrics.heart_rate_status(139.9), "WARN_HIGH")
        self.assertEqual(
            SimulatedBiometrics.heart_rate_status(140.0),
            "CRITICAL_HIGH",
        )


if __name__ == "__main__":
    unittest.main()
