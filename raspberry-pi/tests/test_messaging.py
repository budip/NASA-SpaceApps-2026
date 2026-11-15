from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.main import create_app
from app.models import CrewMessageCreate
from app.storage import StatusStore


class CrewMessagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.store = StatusStore(
            Path(self.temporary_directory.name) / "astra.db"
        )
        self.store.initialize()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_message_is_queued_then_acknowledged(self) -> None:
        created = self.store.create_message(
            CrewMessageCreate(
                recipient_id="astronaut-1",
                priority="CAUTION",
                text="Return to the station airlock.",
            )
        )

        self.assertEqual(created.status, "queued")
        self.assertIsNone(created.delivered_at)
        pending = self.store.messages(
            recipient_id="astronaut-1",
            pending_only=True,
        )
        self.assertEqual([message.id for message in pending], [created.id])

        acknowledged = self.store.acknowledge_message(
            created.id,
            "astronaut-1",
        )

        self.assertIsNotNone(acknowledged)
        self.assertEqual(acknowledged.status, "delivered")
        self.assertIsNotNone(acknowledged.delivered_at)
        self.assertEqual(
            self.store.messages(
                recipient_id="astronaut-1",
                pending_only=True,
            ),
            [],
        )

    def test_inbox_is_isolated_by_astronaut(self) -> None:
        first = self.store.create_message(
            CrewMessageCreate(recipient_id="astronaut-1", text="Message one")
        )
        second = self.store.create_message(
            CrewMessageCreate(recipient_id="astronaut-2", text="Message two")
        )

        astronaut_one = self.store.messages(recipient_id="astronaut-1")
        astronaut_two = self.store.messages(recipient_id="astronaut-2")

        self.assertEqual([message.id for message in astronaut_one], [first.id])
        self.assertEqual([message.id for message in astronaut_two], [second.id])
        self.assertIsNone(
            self.store.acknowledge_message(second.id, "astronaut-1")
        )

    def test_after_id_returns_messages_in_queue_order(self) -> None:
        first = self.store.create_message(
            CrewMessageCreate(recipient_id="astronaut-1", text="First")
        )
        second = self.store.create_message(
            CrewMessageCreate(recipient_id="astronaut-1", text="Second")
        )
        third = self.store.create_message(
            CrewMessageCreate(recipient_id="astronaut-1", text="Third")
        )

        messages = self.store.messages(
            recipient_id="astronaut-1",
            after_id=first.id,
        )

        self.assertEqual(
            [message.id for message in messages],
            [second.id, third.id],
        )

    def test_text_is_trimmed_bounded_and_cannot_be_blank(self) -> None:
        request = CrewMessageCreate(
            recipient_id="astronaut-1",
            text="  Check   the oxygen seal.  ",
        )
        self.assertEqual(request.text, "Check the oxygen seal.")

        with self.assertRaises(ValidationError):
            CrewMessageCreate(recipient_id="astronaut-1", text="   ")
        with self.assertRaises(ValidationError):
            CrewMessageCreate(recipient_id="astronaut-1", text="x" * 241)

    def test_openapi_exposes_message_handoff_routes(self) -> None:
        paths = create_app().openapi()["paths"]

        self.assertIn("/api/v1/crew", paths)
        self.assertIn("post", paths["/api/v1/messages"])
        self.assertIn("get", paths["/api/v1/messages"])
        self.assertIn("post", paths["/api/v1/messages/{message_id}/ack"])


if __name__ == "__main__":
    unittest.main()
