from __future__ import annotations

import tempfile
import unittest
from collections.abc import Iterable
from pathlib import Path

from app.analysis import BaselineAnalyzer
from app.models import SensorSample, SensorValues, SourceName, utc_now
from app.service import AstraService
from app.storage import StatusStore


class SequenceSensor:
    source: SourceName = "simulated"

    def __init__(self, readings: Iterable[float | Exception]) -> None:
        self._readings = iter(readings)

    def read(self) -> SensorSample:
        reading = next(self._readings)
        if isinstance(reading, Exception):
            raise reading
        return SensorSample(
            timestamp=utc_now(),
            sensors=SensorValues(
                temperature_c=reading,
                humidity_pct=40.0,
                pressure_hpa=1012.0,
            ),
            source=self.source,
        )


class AstraServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_restart_restores_baseline_from_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = StatusStore(Path(temporary_directory) / "astra.db")
            store.initialize()
            original = AstraService(
                sensor=SequenceSensor([22.0, 22.1, 21.9, 22.0]),
                analyzer=BaselineAnalyzer(
                    minimum_samples=3,
                    confirmation_samples=1,
                ),
                store=store,
                sample_interval_seconds=60.0,
                restore_baseline=False,
            )
            for _ in range(4):
                await original.sample_once()

            restarted = AstraService(
                sensor=SequenceSensor([22.0]),
                analyzer=BaselineAnalyzer(
                    minimum_samples=3,
                    confirmation_samples=1,
                ),
                store=store,
                sample_interval_seconds=60.0,
                restore_baseline=True,
            )
            await restarted.start()
            try:
                self.assertIsNotNone(restarted.latest)
                self.assertEqual(restarted.latest.status, "NORMAL")
                self.assertGreaterEqual(restarted.analyzer.baseline_size, 3)
            finally:
                await restarted.stop()

    async def test_sampling_failure_marks_cached_and_degrades_health(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = StatusStore(Path(temporary_directory) / "astra.db")
            store.initialize()
            service = AstraService(
                sensor=SequenceSensor([22.0, RuntimeError("sensor failed")]),
                analyzer=BaselineAnalyzer(
                    minimum_samples=2,
                    confirmation_samples=1,
                ),
                store=store,
                sample_interval_seconds=1.0,
                restore_baseline=False,
            )

            await service.sample_once()
            self.assertEqual(service.health_snapshot()["status"], "ok")

            with self.assertRaises(RuntimeError):
                await service.sample_once()

            self.assertEqual(service.latest.source, "cached")
            health = service.health_snapshot()
            self.assertEqual(health["status"], "degraded")
            self.assertEqual(health["consecutive_failures"], 1)
            self.assertEqual(health["last_error"], "RuntimeError")


if __name__ == "__main__":
    unittest.main()
