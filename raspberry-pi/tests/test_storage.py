from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.models import (
    BiometricQuality,
    Biometrics,
    BloodPressure,
    DataQuality,
    DerivedFeatures,
    OrientationDegrees,
    SensorValues,
    StatusResponse,
    TaskMessage,
    SuitPressure,
    SuitTemperature,
    Vector3,
)
from app.storage import StatusStore


class StatusStoreTests(unittest.TestCase):
    def test_initializes_and_records_a_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = StatusStore(Path(temporary_directory) / "astra.db")
            store.initialize()
            store.record(
                StatusResponse(
                    timestamp=datetime.now(timezone.utc),
                    status="NORMAL",
                    score=0.1,
                    summary="Conditions are within the learned baseline.",
                    sensors=SensorValues(temperature_c=22.4),
                    source="simulated",
                )
            )

            self.assertEqual(store.count(), 1)

    def test_loads_only_baseline_eligible_values_for_matching_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = StatusStore(Path(temporary_directory) / "astra.db")
            store.initialize()

            def record(status: str, score: float, source: str, value: float) -> None:
                store.record(
                    StatusResponse(
                        timestamp=datetime.now(timezone.utc),
                        status=status,
                        score=score,
                        summary="test",
                        sensors=SensorValues(temperature_c=value),
                        source=source,
                    )
                )

            record("LEARNING", 0.0, "simulated", 20.0)
            record("NORMAL", 0.1, "simulated", 21.0)
            record("NORMAL", 1.0, "simulated", 99.0)
            record("NORMAL", 0.1, "live", 30.0)

            restored = store.load_baseline_values("simulated", limit=10)

            self.assertEqual(
                [item.temperature_c for item in restored],
                [20.0, 21.0],
            )

    def test_recent_history_is_chronological_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = StatusStore(Path(temporary_directory) / "astra.db")
            store.initialize()
            for value in (20.0, 21.0, 22.0):
                store.record(
                    StatusResponse(
                        timestamp=datetime.now(timezone.utc),
                        status="NORMAL",
                        score=0.1,
                        summary="test",
                        sensors=SensorValues(temperature_c=value),
                        source="simulated",
                    )
                )

            recent = store.recent(limit=2)

            self.assertEqual(
                [item.sensors.temperature_c for item in recent],
                [21.0, 22.0],
            )

    def test_migrates_old_database_and_round_trips_motion_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "astra.db"
            store = StatusStore(database_path)
            store.initialize()
            store.record(
                StatusResponse(
                    timestamp=datetime.now(timezone.utc),
                    status="NORMAL",
                    score=0.1,
                    summary="test",
                    sensors=SensorValues(
                        acceleration_g=Vector3(x=0.1, y=0.2, z=1.0),
                        gyroscope_rps=Vector3(x=0.01, y=0.02, z=0.03),
                        magnetic_uT=Vector3(x=10.0, y=20.0, z=30.0),
                        orientation_deg=OrientationDegrees(
                            pitch=1.0,
                            roll=2.0,
                            yaw=3.0,
                        ),
                    ),
                    source="live",
                    features=DerivedFeatures(
                        acceleration_magnitude_g=1.01,
                        motion_rms_g=0.02,
                        peak_acceleration_g=1.05,
                        rotation_rms_rps=0.03,
                        orientation_change_deg=2.0,
                    ),
                    quality=DataQuality(
                        overall_score=0.95,
                        sample_count=19,
                        expected_sample_count=20,
                        valid_ratio=1.0,
                        flags=["test_flag"],
                    ),
                    biometrics=Biometrics(
                        timestamp=datetime.now(timezone.utc),
                        heart_rate_bpm=72.0,
                        blood_pressure=BloodPressure(
                            systolic_mm_hg=118.0,
                            diastolic_mm_hg=76.0,
                        ),
                        oxygen_saturation_pct=98.0,
                        body_temperature_c=36.8,
                        source="simulated",
                        quality=BiometricQuality(
                            overall_score=1.0,
                            valid_ratio=1.0,
                            flags=["simulated_biometrics"],
                        ),
                    ),
                    suit_pressure=SuitPressure(
                        timestamp=datetime.now(timezone.utc),
                        pressure_hpa=296.0,
                        pressure_psi=4.29,
                        status="NOMINAL",
                        source="simulated",
                        flags=["simulated_suit_pressure"],
                    ),
                    suit_temperature=SuitTemperature(
                        timestamp=datetime.now(timezone.utc),
                        temperature_c=24.0,
                        status="COMFORT",
                        source="simulated",
                        flags=["simulated_suit_air_temperature"],
                    ),
                    tasks=[
                        TaskMessage(
                            id="TASK-001",
                            priority="ALERT",
                            category="navigation",
                            text="Return to station.",
                            issued_at=datetime.now(timezone.utc),
                            source="simulated",
                        )
                    ],
                )
            )

            result = store.recent(limit=1)[0]
            reading = result.sensors
            self.assertEqual(reading.acceleration_g.z, 1.0)
            self.assertEqual(reading.gyroscope_rps.y, 0.02)
            self.assertEqual(reading.magnetic_uT.x, 10.0)
            self.assertEqual(reading.orientation_deg.yaw, 3.0)
            self.assertEqual(result.features.motion_rms_g, 0.02)
            self.assertEqual(result.quality.overall_score, 0.95)
            self.assertEqual(result.quality.flags, ["test_flag"])
            self.assertEqual(result.biometrics.heart_rate_bpm, 72.0)
            self.assertEqual(
                result.biometrics.blood_pressure.systolic_mm_hg,
                118.0,
            )
            self.assertEqual(result.biometrics.source, "simulated")
            self.assertEqual(result.suit_pressure.pressure_hpa, 296.0)
            self.assertEqual(result.suit_pressure.status, "NOMINAL")
            self.assertEqual(result.suit_temperature.temperature_c, 24.0)
            self.assertEqual(result.suit_temperature.status, "COMFORT")
            self.assertEqual(result.tasks[0].id, "TASK-001")
            self.assertEqual(result.tasks[0].priority, "ALERT")


if __name__ == "__main__":
    unittest.main()
