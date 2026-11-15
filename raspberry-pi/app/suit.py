from __future__ import annotations

import random
from typing import Protocol

from app.models import SuitPressure, SuitTemperature, utc_now

HPA_PER_PSI = 68.9475729


def pressure_status(pressure_hpa: float | None) -> str:
    if pressure_hpa is None:
        return "UNAVAILABLE"
    if pressure_hpa <= 248.0:
        return "CRITICAL_LOW"
    if pressure_hpa <= 276.0:
        return "WARN_LOW"
    if pressure_hpa >= 455.0:
        return "CRITICAL_HIGH"
    if pressure_hpa >= 365.0:
        return "WARN_HIGH"
    return "NOMINAL"


def temperature_status(temperature_c: float | None) -> str:
    if temperature_c is None:
        return "UNAVAILABLE"
    if temperature_c < 10.0:
        return "CRITICAL_LOW"
    if temperature_c < 20.0:
        return "WARN_LOW"
    if temperature_c > 43.0:
        return "CRITICAL_HIGH"
    if temperature_c > 30.0:
        return "WARN_HIGH"
    return "COMFORT"


class SuitTelemetrySource(Protocol):
    def read(self) -> tuple[SuitPressure, SuitTemperature]:
        """Return pressure and suit-air temperature with explicit provenance."""


class DisabledSuitTelemetry:
    def read(self) -> tuple[SuitPressure, SuitTemperature]:
        return (
            SuitPressure(flags=["suit_pressure_unavailable"]),
            SuitTemperature(flags=["suit_temperature_unavailable"]),
        )


class SimulatedSuitTelemetry:
    """Smooth demo suit values; never derived from ambient Sense HAT data."""

    def __init__(self, seed: int = 2026) -> None:
        self._random = random.Random(seed)
        self._pressure_hpa = 296.0
        self._temperature_c = 24.0

    def read(self) -> tuple[SuitPressure, SuitTemperature]:
        self._pressure_hpa = self._next(
            self._pressure_hpa,
            center=296.0,
            noise=0.65,
            minimum=286.0,
            maximum=306.0,
        )
        self._temperature_c = self._next(
            self._temperature_c,
            center=24.0,
            noise=0.08,
            minimum=22.0,
            maximum=27.0,
        )
        timestamp = utc_now()
        pressure_hpa = round(self._pressure_hpa, 1)
        temperature_c = round(self._temperature_c, 1)
        return (
            SuitPressure(
                timestamp=timestamp,
                pressure_hpa=pressure_hpa,
                pressure_psi=round(pressure_hpa / HPA_PER_PSI, 2),
                status=pressure_status(pressure_hpa),
                source="simulated",
                flags=[
                    "simulated_suit_pressure",
                    "sense_hat_pressure_is_ambient_not_suit_pressure",
                    "prototype_thresholds_not_certified_alarms",
                ],
            ),
            SuitTemperature(
                timestamp=timestamp,
                temperature_c=temperature_c,
                status=temperature_status(temperature_c),
                source="simulated",
                flags=[
                    "simulated_suit_air_temperature",
                    "critical_limits_adapted_from_internal_touch_temperature",
                    "prototype_thresholds_not_certified_alarms",
                ],
            ),
        )

    def _next(
        self,
        current: float,
        center: float,
        noise: float,
        minimum: float,
        maximum: float,
    ) -> float:
        mean_reversion = (center - current) * 0.12
        candidate = current + mean_reversion + self._random.gauss(0.0, noise)
        return min(max(candidate, minimum), maximum)
