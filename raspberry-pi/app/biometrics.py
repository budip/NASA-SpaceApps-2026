from __future__ import annotations

import random
from typing import Protocol

from app.models import (
    BiometricQuality,
    Biometrics,
    BloodPressure,
    utc_now,
)


class BiometricSource(Protocol):
    def read(self) -> Biometrics:
        """Return one explicitly sourced biometric snapshot."""


class DisabledBiometrics:
    def read(self) -> Biometrics:
        return Biometrics(
            source="unavailable",
            quality=BiometricQuality(flags=["biometrics_disabled"]),
        )


class SimulatedBiometrics:
    """Smooth, bounded mock crew data for UI and API integration demos."""

    def __init__(self, seed: int = 2026) -> None:
        self._random = random.Random(seed)
        self._values = {
            "heart_rate_bpm": 72.0,
            "systolic_mm_hg": 118.0,
            "diastolic_mm_hg": 76.0,
            "oxygen_saturation_pct": 98.0,
            "body_temperature_c": 36.8,
        }

    def read(self) -> Biometrics:
        self._values["heart_rate_bpm"] = self._next(
            "heart_rate_bpm", center=72.0, noise=1.2, minimum=58.0, maximum=96.0
        )
        self._values["systolic_mm_hg"] = self._next(
            "systolic_mm_hg", center=118.0, noise=1.0, minimum=105.0, maximum=132.0
        )
        self._values["diastolic_mm_hg"] = self._next(
            "diastolic_mm_hg", center=76.0, noise=0.8, minimum=66.0, maximum=86.0
        )
        self._values["oxygen_saturation_pct"] = self._next(
            "oxygen_saturation_pct",
            center=98.0,
            noise=0.18,
            minimum=96.0,
            maximum=99.5,
        )
        self._values["body_temperature_c"] = self._next(
            "body_temperature_c",
            center=36.8,
            noise=0.035,
            minimum=36.3,
            maximum=37.3,
        )

        heart_rate_bpm = round(self._values["heart_rate_bpm"], 1)
        return Biometrics(
            timestamp=utc_now(),
            heart_rate_bpm=heart_rate_bpm,
            blood_pressure=BloodPressure(
                systolic_mm_hg=round(self._values["systolic_mm_hg"]),
                diastolic_mm_hg=round(self._values["diastolic_mm_hg"]),
            ),
            oxygen_saturation_pct=round(
                self._values["oxygen_saturation_pct"], 1
            ),
            body_temperature_c=round(self._values["body_temperature_c"], 2),
            heart_rate_status=self.heart_rate_status(heart_rate_bpm),
            source="simulated",
            quality=BiometricQuality(
                overall_score=1.0,
                valid_ratio=1.0,
                sample_age_seconds=0.0,
                flags=["simulated_biometrics"],
            ),
        )

    @staticmethod
    def heart_rate_status(heart_rate_bpm: float | None) -> str:
        if heart_rate_bpm is None:
            return "UNAVAILABLE"
        if heart_rate_bpm >= 140.0:
            return "CRITICAL_HIGH"
        if heart_rate_bpm >= 120.0:
            return "WARN_HIGH"
        return "NOMINAL"

    def _next(
        self,
        field: str,
        center: float,
        noise: float,
        minimum: float,
        maximum: float,
    ) -> float:
        current = self._values[field]
        mean_reversion = (center - current) * 0.12
        candidate = current + mean_reversion + self._random.gauss(0.0, noise)
        return min(max(candidate, minimum), maximum)
