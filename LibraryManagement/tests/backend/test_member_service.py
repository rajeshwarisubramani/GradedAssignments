import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from backend.services.member_service import MemberService


class MemberServiceTests(unittest.TestCase):
    def _make_service(self) -> tuple[tempfile.TemporaryDirectory, Path, MemberService]:
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        members_file = root / "members.json"
        members_file.write_text(
            json.dumps(
                [
                    {
                        "member_id": "M001",
                        "name": "John Doe",
                        "email": "john@example.com",
                        "phone": "555-0101",
                        "membership_date": "2024-01-15",
                        "status": "active",
                        "address": {"street": "123 Main St", "city": "Springfield", "postal_code": "12345"},
                    },
                    {
                        "member_id": "M002",
                        "name": "John Doe",
                        "contact_info": "john2@example.com",
                        "age": 20,
                    },
                ]
            ),
            encoding="utf-8",
        )
        return temp_dir, members_file, MemberService(file_path=members_file)

    def test_fetch_all_members(self):
        temp_dir, _, service = self._make_service()
        self.addCleanup(temp_dir.cleanup)

        members = service.fetch_all_members()

        self.assertEqual(len(members), 2)
        self.assertIn("membership_date", members[0])

    def test_fetch_members_by_name_returns_array(self):
        temp_dir, _, service = self._make_service()
        self.addCleanup(temp_dir.cleanup)

        members = service.fetch_members_by_name("john doe")

        self.assertEqual(len(members), 2)

    def test_fetch_member_by_id(self):
        temp_dir, _, service = self._make_service()
        self.addCleanup(temp_dir.cleanup)

        member = service.fetch_member_by_id("M001")

        self.assertIsNotNone(member)
        self.assertEqual(member["email"], "john@example.com")

    def test_add_member_sets_membership_date_to_today(self):
        temp_dir, _, service = self._make_service()
        self.addCleanup(temp_dir.cleanup)

        created = service.add_member(
            "M003",
            "Alice",
            "alice@example.com",
            "555-0202",
            address={"street": "9 Elm St", "city": "Metropolis", "postal_code": "54321"},
        )

        self.assertEqual(created["membership_date"], date.today().isoformat())
        self.assertEqual(created["address"]["city"], "Metropolis")

    def test_update_member_information(self):
        temp_dir, _, service = self._make_service()
        self.addCleanup(temp_dir.cleanup)

        updated = service.update_member(
            "M001",
            {
                "phone": "555-9999",
                "status": "ACTIVE",
                "address": {"street": "99 Oak Ave", "city": "Smallville", "postal_code": "60606"},
            },
        )

        self.assertEqual(updated["phone"], "555-9999")
        self.assertEqual(updated["status"], "active")
        self.assertEqual(updated["address"]["city"], "Smallville")


if __name__ == "__main__":
    unittest.main()

