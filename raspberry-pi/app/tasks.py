from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Protocol

from app.models import TaskMessage, TaskPriority, utc_now

DEFAULT_TASK_CATALOG = Path(__file__).with_name("data") / "task_messages.txt"


class TaskSource(Protocol):
    def read(self) -> list[TaskMessage]:
        """Return the current task list."""


class DisabledTaskSource:
    def read(self) -> list[TaskMessage]:
        return []


class SimulatedTaskSource:
    def __init__(
        self,
        catalog_path: Path = DEFAULT_TASK_CATALOG,
        interval_seconds: float = 300.0,
        max_items: int = 3,
        seed: int = 2026,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if max_items <= 0:
            raise ValueError("max_items must be positive")
        self.interval_seconds = interval_seconds
        self._random = random.Random(seed)
        self._catalog = self._load_catalog(catalog_path)
        self.max_items = min(max_items, len(self._catalog))
        self._current: list[TaskMessage] = []
        self._current_indices: tuple[int, ...] = ()
        self._next_change = 0.0

    def read(self) -> list[TaskMessage]:
        now = time.monotonic()
        if not self._current or now >= self._next_change:
            item_count = self._random.randint(1, self.max_items)
            indices = tuple(
                self._random.sample(range(len(self._catalog)), item_count)
            )
            if indices == self._current_indices and len(self._catalog) > item_count:
                replacement = next(
                    index
                    for index in range(len(self._catalog))
                    if index not in indices
                )
                indices = (replacement, *indices[1:])

            issued_at = utc_now()
            self._current = [
                TaskMessage(
                    id=f"TASK-{index + 1:03d}",
                    priority=self._catalog[index][0],
                    category=self._catalog[index][1],
                    text=self._catalog[index][2],
                    issued_at=issued_at,
                    source="simulated",
                )
                for index in indices
            ]
            self._current_indices = indices
            self._next_change = now + self.interval_seconds
        return list(self._current)

    @staticmethod
    def _load_catalog(
        path: Path,
    ) -> list[tuple[TaskPriority, str, str]]:
        catalog: list[tuple[TaskPriority, str, str]] = []
        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.split("|", maxsplit=2)]
            if len(parts) != 3:
                raise ValueError(f"Invalid task catalog line {line_number}")
            priority, category, text = parts
            if priority not in {"INFO", "ADVISORY", "CAUTION", "ALERT"}:
                raise ValueError(
                    f"Invalid task priority on catalog line {line_number}"
                )
            catalog.append((priority, category, text))
        if not catalog:
            raise ValueError("Task catalog is empty")
        return catalog
