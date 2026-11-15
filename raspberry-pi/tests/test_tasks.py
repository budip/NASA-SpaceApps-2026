from __future__ import annotations

import unittest

from app.tasks import DEFAULT_TASK_CATALOG, SimulatedTaskSource


class SimulatedTaskSourceTests(unittest.TestCase):
    def test_catalog_contains_exactly_two_hundred_messages(self) -> None:
        source = SimulatedTaskSource(DEFAULT_TASK_CATALOG, seed=3)

        self.assertEqual(len(source._catalog), 200)

    def test_task_is_stable_until_interval_expires(self) -> None:
        source = SimulatedTaskSource(interval_seconds=60.0, seed=3)

        first = source.read()
        second = source.read()

        self.assertEqual(
            [task.id for task in first],
            [task.id for task in second],
        )
        self.assertEqual(
            [task.issued_at for task in first],
            [task.issued_at for task in second],
        )
        self.assertTrue(all(task.source == "simulated" for task in first))

    def test_batch_contains_one_to_three_unique_tasks(self) -> None:
        source = SimulatedTaskSource(interval_seconds=60.0, seed=3)

        batch = source.read()

        self.assertGreaterEqual(len(batch), 1)
        self.assertLessEqual(len(batch), 3)
        self.assertEqual(len({task.id for task in batch}), len(batch))

    def test_expired_interval_selects_a_new_task(self) -> None:
        source = SimulatedTaskSource(interval_seconds=60.0, seed=3)
        first = source.read()

        source._next_change = 0.0
        second = source.read()

        self.assertNotEqual(
            [task.id for task in first],
            [task.id for task in second],
        )
        self.assertTrue(
            all(
                task.priority in {"INFO", "ADVISORY", "CAUTION", "ALERT"}
                for task in second
            )
        )


if __name__ == "__main__":
    unittest.main()
