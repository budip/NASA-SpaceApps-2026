from __future__ import annotations

import math
import statistics
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass

from app.models import SensorSample, SensorValues, StatusName, StatusResponse

SENSOR_LABELS = {
    "temperature_c": "temperature",
    "humidity_pct": "humidity",
    "pressure_hpa": "pressure",
}

# Prevent tiny simulated noise from making harmless changes look extreme.
DISPERSION_FLOORS = {
    "temperature_c": 0.20,
    "humidity_pct": 0.50,
    "pressure_hpa": 0.30,
}


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    candidate: StatusName
    score: float
    strongest_sensor: str | None
    strongest_z_score: float


class BaselineAnalyzer:
    def __init__(self, minimum_samples: int = 20, confirmation_samples: int = 2):
        if minimum_samples < 2:
            raise ValueError("minimum_samples must be at least 2")
        if confirmation_samples < 1:
            raise ValueError("confirmation_samples must be at least 1")

        self.minimum_samples = minimum_samples
        self.confirmation_samples = confirmation_samples
        self._history: deque[dict[str, float]] = deque(maxlen=300)
        self._current_status: StatusName = "LEARNING"
        self._pending_status: StatusName | None = None
        self._pending_count = 0

    @property
    def baseline_size(self) -> int:
        return len(self._history)

    @property
    def history_capacity(self) -> int:
        return self._history.maxlen or 0

    def restore(self, samples: Iterable[SensorValues]) -> int:
        """Seed the rolling baseline from previously accepted local history."""
        self._history.clear()
        self._current_status = "LEARNING"
        self._pending_status = None
        self._pending_count = 0
        restored = 0
        for sensors in samples:
            values = self._available_sensor_values(sensors)
            if not values:
                continue
            self._history.append(values)
            restored += 1

        if len(self._history) >= self.minimum_samples:
            self._current_status = "NORMAL"
        return restored

    def evaluate(self, sample: SensorSample) -> StatusResponse:
        values = self._available_values(sample)

        if len(self._history) < self.minimum_samples:
            if values:
                self._history.append(values)
            learned = min(len(self._history), self.minimum_samples)
            return StatusResponse(
                timestamp=sample.timestamp,
                status="LEARNING",
                score=0.0,
                summary=f"Learning surroundings ({learned}/{self.minimum_samples}).",
                sensors=sample.sensors,
                source=sample.source,
                features=sample.features,
                quality=sample.quality,
            )

        result = self._analyze(values)
        status = self._stabilize(result.candidate)

        # Keep ordinary conditions in the rolling baseline but avoid teaching a
        # detected event to look normal.
        if values and result.candidate == "NORMAL":
            self._history.append(values)

        return StatusResponse(
            timestamp=sample.timestamp,
            status=status,
            score=round(result.score, 3),
            summary=self._summary(status, result, values),
            sensors=sample.sensors,
            source=sample.source,
            features=sample.features,
            quality=sample.quality,
        )

    @staticmethod
    def _available_values(sample: SensorSample) -> dict[str, float]:
        return BaselineAnalyzer._available_sensor_values(sample.sensors)

    @staticmethod
    def _available_sensor_values(sensors: SensorValues) -> dict[str, float]:
        values: dict[str, float] = {}
        for field in SENSOR_LABELS:
            value = getattr(sensors, field)
            if value is not None and math.isfinite(value):
                values[field] = value
        return values

    def _analyze(self, values: dict[str, float]) -> AnalysisResult:
        if not values:
            return AnalysisResult("CAUTION", 1.0, None, 0.0)

        strongest_sensor = None
        strongest_z = 0.0
        for field, value in values.items():
            history = [row[field] for row in self._history if field in row]
            if len(history) < 2:
                continue
            center = statistics.fmean(history)
            spread = max(statistics.pstdev(history), DISPERSION_FLOORS[field])
            z_score = abs(value - center) / spread
            if z_score > strongest_z:
                strongest_sensor = field
                strongest_z = z_score

        if strongest_z >= 6.0:
            candidate: StatusName = "ALERT"
        elif strongest_z >= 3.0:
            candidate = "CAUTION"
        else:
            candidate = "NORMAL"

        return AnalysisResult(
            candidate=candidate,
            score=min(strongest_z / 6.0, 1.0),
            strongest_sensor=strongest_sensor,
            strongest_z_score=strongest_z,
        )

    def _stabilize(self, candidate: StatusName) -> StatusName:
        if self._current_status == "LEARNING" and candidate == "NORMAL":
            self._current_status = "NORMAL"
            return self._current_status

        if candidate == self._current_status:
            self._pending_status = None
            self._pending_count = 0
            return self._current_status

        if candidate != self._pending_status:
            self._pending_status = candidate
            self._pending_count = 1
        else:
            self._pending_count += 1

        if self._pending_count >= self.confirmation_samples:
            self._current_status = candidate
            self._pending_status = None
            self._pending_count = 0
        return self._current_status

    @staticmethod
    def _summary(
        status: StatusName,
        result: AnalysisResult,
        values: dict[str, float],
    ) -> str:
        if not values:
            return "Sensor readings are unavailable; check the backpack."
        if status == "NORMAL":
            return "Conditions are within the learned baseline."
        if status == "CAUTION":
            label = SENSOR_LABELS.get(result.strongest_sensor or "", "condition")
            return f"Change detected in {label}; check conditions."
        if status == "ALERT":
            label = SENSOR_LABELS.get(result.strongest_sensor or "", "condition")
            return f"Strong change detected in {label}."
        return "Learning surroundings."
