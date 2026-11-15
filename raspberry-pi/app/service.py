from __future__ import annotations

import asyncio
import logging
import time

from app.analysis import BaselineAnalyzer
from app.biometrics import BiometricSource, DisabledBiometrics
from app.models import CrewMessage, CrewMessageCreate, StatusResponse
from app.processing import SensorProcessor
from app.sensors import SensorSource
from app.storage import StatusStore
from app.suit import DisabledSuitTelemetry, SuitTelemetrySource
from app.tasks import DisabledTaskSource, TaskSource

LOGGER = logging.getLogger(__name__)


class AstraService:
    def __init__(
        self,
        sensor: SensorSource,
        analyzer: BaselineAnalyzer,
        store: StatusStore,
        sample_interval_seconds: float,
        restore_baseline: bool = True,
        processor: SensorProcessor | None = None,
        biometrics: BiometricSource | None = None,
        tasks: TaskSource | None = None,
        suit: SuitTelemetrySource | None = None,
    ) -> None:
        self.sensor = sensor
        self.analyzer = analyzer
        self.store = store
        self.sample_interval_seconds = sample_interval_seconds
        self.restore_baseline = restore_baseline
        self.processor = processor or SensorProcessor(expected_imu_samples=1)
        self.biometrics = biometrics or DisabledBiometrics()
        self.tasks = tasks or DisabledTaskSource()
        self.suit = suit or DisabledSuitTelemetry()
        self.latest: StatusResponse | None = None
        self.consecutive_failures = 0
        self.last_error: str | None = None
        self._last_success_monotonic: float | None = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self.store.initialize()
        if self.restore_baseline:
            saved_values = await asyncio.to_thread(
                self.store.load_baseline_values,
                self.sensor.source,
                self.analyzer.history_capacity,
            )
            restored = self.analyzer.restore(saved_values)
            if restored:
                LOGGER.info(
                    "Restored %d %s baseline samples",
                    restored,
                    self.sensor.source,
                )
        await self.sample_once()
        self._task = asyncio.create_task(self._run(), name="astra-sampler")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        close_sensor = getattr(self.sensor, "close", None)
        if close_sensor is not None:
            await asyncio.to_thread(close_sensor)

    async def sample_once(self) -> StatusResponse:
        try:
            sample = await asyncio.to_thread(self.sensor.read)
            sample = self.processor.process(sample)
            response = self.analyzer.evaluate(sample)
            biometrics = await asyncio.to_thread(self.biometrics.read)
            tasks = await asyncio.to_thread(self.tasks.read)
            suit_pressure, suit_temperature = await asyncio.to_thread(
                self.suit.read
            )
            response = response.model_copy(
                update={
                    "biometrics": biometrics,
                    "suit_pressure": suit_pressure,
                    "suit_temperature": suit_temperature,
                    "tasks": tasks,
                }
            )
            await asyncio.to_thread(self.store.record, response)
        except Exception as error:
            self._record_failure(error)
            raise

        self.latest = response
        self.consecutive_failures = 0
        self.last_error = None
        self._last_success_monotonic = time.monotonic()
        return response

    def health_snapshot(self) -> dict[str, object]:
        sample_age = None
        if self._last_success_monotonic is not None:
            sample_age = max(0.0, time.monotonic() - self._last_success_monotonic)

        stale_after = max(5.0, self.sample_interval_seconds * 3.0)
        healthy = (
            sample_age is not None
            and sample_age <= stale_after
            and self.consecutive_failures == 0
        )
        return {
            "status": "ok" if healthy else "degraded",
            "sample_age_seconds": (
                round(sample_age, 3) if sample_age is not None else None
            ),
            "baseline_samples": self.analyzer.baseline_size,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
        }

    async def recent_history(self, limit: int = 120) -> list[StatusResponse]:
        return await asyncio.to_thread(self.store.recent, limit)

    async def send_message(self, request: CrewMessageCreate) -> CrewMessage:
        return await asyncio.to_thread(self.store.create_message, request)

    async def messages(
        self,
        recipient_id: str | None = None,
        after_id: int = 0,
        pending_only: bool = False,
        limit: int = 50,
    ) -> list[CrewMessage]:
        return await asyncio.to_thread(
            self.store.messages,
            recipient_id,
            after_id,
            pending_only,
            limit,
        )

    async def acknowledge_message(
        self,
        message_id: int,
        recipient_id: str,
    ) -> CrewMessage | None:
        return await asyncio.to_thread(
            self.store.acknowledge_message,
            message_id,
            recipient_id,
        )

    def _record_failure(self, error: Exception) -> None:
        self.consecutive_failures += 1
        self.last_error = type(error).__name__
        if self.latest is not None and self.latest.source != "cached":
            self.latest = self.latest.model_copy(update={"source": "cached"})

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.sample_interval_seconds)
            try:
                await self.sample_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.exception("Sensor sampling failed; retaining last known payload")
