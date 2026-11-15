from __future__ import annotations

import math
import statistics
from collections import deque

from app.models import (
    DataQuality,
    DerivedFeatures,
    OrientationDegrees,
    SensorSample,
    SensorValues,
    Vector3,
)

ENVIRONMENT_FIELDS = ("temperature_c", "humidity_pct", "pressure_hpa")
ENVIRONMENT_SPIKE_FLOORS = {
    "temperature_c": 0.8,
    "humidity_pct": 3.0,
    "pressure_hpa": 2.0,
}


class SensorProcessor:
    """Convert noisy sensor windows into compact, quality-scored edge data."""

    def __init__(
        self,
        expected_imu_samples: int = 20,
        environment_window: int = 5,
    ) -> None:
        if expected_imu_samples < 1:
            raise ValueError("expected_imu_samples must be positive")
        if environment_window < 3:
            raise ValueError("environment_window must be at least 3")

        self.expected_imu_samples = expected_imu_samples
        self._environment_history = {
            field: deque(maxlen=environment_window) for field in ENVIRONMENT_FIELDS
        }
        self._environment_ema: dict[str, float] = {}
        self._vector_ema: dict[str, Vector3] = {}
        self._orientation_ema: OrientationDegrees | None = None

    def process(self, sample: SensorSample) -> SensorSample:
        window = sample.imu_window or [sample.sensors]
        flags: list[str] = []

        environment = {
            field: self._filter_environment(
                field,
                getattr(sample.sensors, field),
                flags,
            )
            for field in ENVIRONMENT_FIELDS
        }

        acceleration_samples = self._vectors(window, "acceleration_g")
        gyroscope_samples = self._vectors(window, "gyroscope_rps")
        magnetic_samples = self._vectors(window, "magnetic_uT")
        orientation_samples = self._orientations(window)

        acceleration = self._smooth_vector(
            "acceleration_g",
            self._mean_vector(acceleration_samples),
            alpha=0.45,
        )
        gyroscope = self._smooth_vector(
            "gyroscope_rps",
            self._mean_vector(gyroscope_samples),
            alpha=0.45,
        )
        magnetic = self._smooth_vector(
            "magnetic_uT",
            self._median_vector(magnetic_samples),
            alpha=0.25,
        )
        orientation = self._smooth_orientation(
            self._mean_orientation(orientation_samples),
            alpha=0.35,
        )

        filtered = SensorValues(
            **environment,
            acceleration_g=acceleration,
            gyroscope_rps=gyroscope,
            magnetic_uT=magnetic,
            orientation_deg=orientation,
        )
        features = self._features(
            acceleration_samples,
            gyroscope_samples,
            orientation_samples,
            acceleration,
        )
        quality = self._quality(sample, window, flags)

        return sample.model_copy(
            update={
                "sensors": filtered,
                "features": features,
                "quality": quality,
            }
        )

    def _filter_environment(
        self,
        field: str,
        value: float | None,
        flags: list[str],
    ) -> float | None:
        if value is None or not math.isfinite(value):
            flags.append(f"missing_{field}")
            return None

        history = self._environment_history[field]
        if len(history) >= 3:
            center = statistics.median(history)
            deviations = [abs(item - center) for item in history]
            mad = statistics.median(deviations)
            threshold = max(6.0 * 1.4826 * mad, ENVIRONMENT_SPIKE_FLOORS[field])
            if abs(value - center) > threshold:
                flags.append(f"spike_suppressed_{field}")

        history.append(value)
        target = float(statistics.median(history))
        previous = self._environment_ema.get(field)
        filtered = target if previous is None else previous + 0.25 * (target - previous)
        self._environment_ema[field] = filtered
        return round(filtered, 3)

    @staticmethod
    def _vectors(window: list[SensorValues], field: str) -> list[Vector3]:
        values: list[Vector3] = []
        for sensors in window:
            vector = getattr(sensors, field)
            if vector is None:
                continue
            components = (vector.x, vector.y, vector.z)
            if all(value is not None and math.isfinite(value) for value in components):
                values.append(vector)
        return values

    @staticmethod
    def _orientations(window: list[SensorValues]) -> list[OrientationDegrees]:
        values: list[OrientationDegrees] = []
        for sensors in window:
            orientation = sensors.orientation_deg
            if orientation is None:
                continue
            components = (orientation.pitch, orientation.roll, orientation.yaw)
            if all(value is not None and math.isfinite(value) for value in components):
                values.append(orientation)
        return values

    @staticmethod
    def _mean_vector(values: list[Vector3]) -> Vector3 | None:
        if not values:
            return None
        return Vector3(
            x=statistics.fmean(value.x for value in values if value.x is not None),
            y=statistics.fmean(value.y for value in values if value.y is not None),
            z=statistics.fmean(value.z for value in values if value.z is not None),
        )

    @staticmethod
    def _median_vector(values: list[Vector3]) -> Vector3 | None:
        if not values:
            return None
        return Vector3(
            x=statistics.median(value.x for value in values if value.x is not None),
            y=statistics.median(value.y for value in values if value.y is not None),
            z=statistics.median(value.z for value in values if value.z is not None),
        )

    def _smooth_vector(
        self,
        name: str,
        value: Vector3 | None,
        alpha: float,
    ) -> Vector3 | None:
        if value is None:
            return None
        previous = self._vector_ema.get(name)
        if previous is None:
            filtered = value
        else:
            filtered = Vector3(
                x=self._lerp(previous.x, value.x, alpha),
                y=self._lerp(previous.y, value.y, alpha),
                z=self._lerp(previous.z, value.z, alpha),
            )
        filtered = Vector3(
            x=self._rounded(filtered.x, 4),
            y=self._rounded(filtered.y, 4),
            z=self._rounded(filtered.z, 4),
        )
        self._vector_ema[name] = filtered
        return filtered

    @staticmethod
    def _mean_orientation(
        values: list[OrientationDegrees],
    ) -> OrientationDegrees | None:
        if not values:
            return None
        return OrientationDegrees(
            pitch=SensorProcessor._circular_mean(
                [value.pitch for value in values if value.pitch is not None]
            ),
            roll=SensorProcessor._circular_mean(
                [value.roll for value in values if value.roll is not None]
            ),
            yaw=SensorProcessor._circular_mean(
                [value.yaw for value in values if value.yaw is not None]
            ),
        )

    def _smooth_orientation(
        self,
        value: OrientationDegrees | None,
        alpha: float,
    ) -> OrientationDegrees | None:
        if value is None:
            return None
        previous = self._orientation_ema
        if previous is None:
            filtered = value
        else:
            filtered = OrientationDegrees(
                pitch=self._angle_lerp(previous.pitch, value.pitch, alpha),
                roll=self._angle_lerp(previous.roll, value.roll, alpha),
                yaw=self._angle_lerp(previous.yaw, value.yaw, alpha),
            )
        filtered = OrientationDegrees(
            pitch=self._rounded(filtered.pitch, 4),
            roll=self._rounded(filtered.roll, 4),
            yaw=self._rounded(filtered.yaw, 4),
        )
        self._orientation_ema = filtered
        return filtered

    def _features(
        self,
        acceleration: list[Vector3],
        gyroscope: list[Vector3],
        orientation: list[OrientationDegrees],
        filtered_acceleration: Vector3 | None,
    ) -> DerivedFeatures:
        acceleration_magnitudes = [self._magnitude(value) for value in acceleration]
        acceleration_mean = self._mean_vector(acceleration)
        motion_rms = None
        if acceleration and acceleration_mean is not None:
            motion_rms = math.sqrt(
                statistics.fmean(
                    (value.x - acceleration_mean.x) ** 2
                    + (value.y - acceleration_mean.y) ** 2
                    + (value.z - acceleration_mean.z) ** 2
                    for value in acceleration
                    if value.x is not None
                    and value.y is not None
                    and value.z is not None
                    and acceleration_mean.x is not None
                    and acceleration_mean.y is not None
                    and acceleration_mean.z is not None
                )
            )

        rotation_rms = None
        if gyroscope:
            rotation_rms = math.sqrt(
                statistics.fmean(self._magnitude(value) ** 2 for value in gyroscope)
            )

        orientation_change = None
        if len(orientation) >= 2:
            first = orientation[0]
            last = orientation[-1]
            deltas = [
                self._angle_distance(first.pitch, last.pitch),
                self._angle_distance(first.roll, last.roll),
                self._angle_distance(first.yaw, last.yaw),
            ]
            orientation_change = math.sqrt(
                statistics.fmean(delta**2 for delta in deltas if delta is not None)
            )

        return DerivedFeatures(
            acceleration_magnitude_g=(
                self._rounded(self._magnitude(filtered_acceleration), 4)
                if filtered_acceleration is not None
                else None
            ),
            motion_rms_g=self._rounded(motion_rms, 4),
            peak_acceleration_g=(
                self._rounded(max(acceleration_magnitudes), 4)
                if acceleration_magnitudes
                else None
            ),
            rotation_rms_rps=self._rounded(rotation_rms, 4),
            orientation_change_deg=self._rounded(orientation_change, 3),
        )

    def _quality(
        self,
        sample: SensorSample,
        window: list[SensorValues],
        flags: list[str],
    ) -> DataQuality:
        sample_count = len(window)
        if sample_count < max(1, math.ceil(self.expected_imu_samples * 0.8)):
            flags.append("low_imu_sample_count")

        valid = 0
        total = 3 + sample_count * 12
        valid += sum(
            getattr(sample.sensors, field) is not None for field in ENVIRONMENT_FIELDS
        )
        for sensors in window:
            for field in ("acceleration_g", "gyroscope_rps", "magnetic_uT"):
                vector = getattr(sensors, field)
                if vector is None:
                    flags.append(f"missing_{field}")
                    continue
                valid += sum(
                    value is not None and math.isfinite(value)
                    for value in (vector.x, vector.y, vector.z)
                )
            orientation = sensors.orientation_deg
            if orientation is None:
                flags.append("missing_orientation_deg")
            else:
                valid += sum(
                    value is not None and math.isfinite(value)
                    for value in (
                        orientation.pitch,
                        orientation.roll,
                        orientation.yaw,
                    )
                )

        valid_ratio = valid / total if total else 0.0
        sample_coverage = min(sample_count / self.expected_imu_samples, 1.0)
        overall = 0.7 * valid_ratio + 0.3 * sample_coverage
        return DataQuality(
            overall_score=round(overall, 3),
            sample_count=sample_count,
            expected_sample_count=self.expected_imu_samples,
            valid_ratio=round(valid_ratio, 3),
            filtered=True,
            flags=sorted(set(flags)),
        )

    @staticmethod
    def _magnitude(value: Vector3) -> float:
        return math.sqrt((value.x or 0.0) ** 2 + (value.y or 0.0) ** 2 + (value.z or 0.0) ** 2)

    @staticmethod
    def _circular_mean(values: list[float]) -> float | None:
        if not values:
            return None
        radians = [math.radians(value) for value in values]
        angle = math.degrees(
            math.atan2(
                statistics.fmean(math.sin(value) for value in radians),
                statistics.fmean(math.cos(value) for value in radians),
            )
        )
        return angle % 360.0

    @staticmethod
    def _angle_lerp(
        start: float | None,
        end: float | None,
        alpha: float,
    ) -> float | None:
        if start is None or end is None:
            return end
        delta = (end - start + 180.0) % 360.0 - 180.0
        return (start + alpha * delta) % 360.0

    @staticmethod
    def _angle_distance(
        start: float | None,
        end: float | None,
    ) -> float | None:
        if start is None or end is None:
            return None
        return abs((end - start + 180.0) % 360.0 - 180.0)

    @staticmethod
    def _lerp(
        start: float | None,
        end: float | None,
        alpha: float,
    ) -> float | None:
        if start is None or end is None:
            return end
        return start + alpha * (end - start)

    @staticmethod
    def _rounded(value: float | None, digits: int) -> float | None:
        return round(value, digits) if value is not None and math.isfinite(value) else None
