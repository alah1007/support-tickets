import tempfile
import unittest
from pathlib import Path

from ticket_store import (
    add_comment,
    create_ticket,
    get_ticket,
    init_db,
    list_comments,
    list_tickets,
    update_ticket,
)


class TicketStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "tickets.sqlite3"
        init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_ticket(self, **overrides):
        data = {
            "title": "Cannot sign in",
            "description": "The password reset link expired.",
            "requester": "Amina",
            "requester_email": "amina@example.com",
            "priority": "High",
            "assigned_to": "Sam",
            "db_path": self.db_path,
        }
        data.update(overrides)
        return create_ticket(**data)

    def test_create_and_retrieve_ticket(self):
        ticket_id = self.make_ticket()
        ticket = get_ticket(ticket_id, self.db_path)
        self.assertEqual(ticket["title"], "Cannot sign in")
        self.assertEqual(ticket["status"], "Open")
        self.assertEqual(ticket["priority"], "High")
        self.assertTrue(ticket["created_at"].endswith("+00:00"))

    def test_filters_and_case_insensitive_search(self):
        self.make_ticket()
        self.make_ticket(title="Printer issue", priority="Low", requester="Omar", requester_email="omar@example.com")
        self.assertEqual(len(list_tickets(priority="High", db_path=self.db_path)), 1)
        self.assertEqual(len(list_tickets(search="AMINA", db_path=self.db_path)), 1)
        self.assertEqual(len(list_tickets(search="missing", db_path=self.db_path)), 0)

    def test_update_ticket(self):
        ticket_id = self.make_ticket()
        self.assertTrue(
            update_ticket(ticket_id, "In progress", "Urgent", "Leila", self.db_path)
        )
        ticket = get_ticket(ticket_id, self.db_path)
        self.assertEqual(ticket["status"], "In progress")
        self.assertEqual(ticket["priority"], "Urgent")
        self.assertEqual(ticket["assigned_to"], "Leila")
        self.assertFalse(update_ticket(999, "Open", "Low", db_path=self.db_path))

    def test_comments_are_saved_in_order(self):
        ticket_id = self.make_ticket()
        add_comment(ticket_id, "Sam", "Started investigating.", self.db_path)
        add_comment(ticket_id, "Sam", "Waiting for a reply.", self.db_path)
        comments = list_comments(ticket_id, self.db_path)
        self.assertEqual([item["body"] for item in comments], [
            "Started investigating.",
            "Waiting for a reply.",
        ])

    def test_invalid_input_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_ticket(title="  ")
        with self.assertRaises(ValueError):
            self.make_ticket(priority="Critical")
        with self.assertRaises(ValueError):
            add_comment(999, "Sam", "Note", self.db_path)


if __name__ == "__main__":
    unittest.main()
