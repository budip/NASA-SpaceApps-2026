from __future__ import annotations

from typing import Protocol

from app.models import SensorSample, SourceName


class SensorSource(Protocol):
    source: SourceName

    def read(self) -> SensorSample:
        """Return one normalized sample without inventing failed readings."""
