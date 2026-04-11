import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from backend.domain.exceptions import ConflictError
from backend.services.transaction_service import MAX_BORROW_DAYS, TransactionService


class TransactionServiceTests(unittest.TestCase):
    def _write_json(self, path: Path, rows: list[dict]) -> None:
        path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def _make_service(
        self,
        books: list[dict] | None = None,
        members: list[dict] | None = None,
        transactions: list[dict] | None = None,
        member_books: list[dict] | None = None,
    ) -> tuple[tempfile.TemporaryDirectory, TransactionService, Path, Path, Path, Path]:
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)

        books_file = root / "books.json"
        members_file = root / "members.json"
        transactions_file = root / "transactions.json"
        member_books_file = root / "member_books.json"

        self._write_json(
            books_file,
            books
            or [
                {
                    "book_id": "B0001",
                    "title": "Book 1",
                    "author": "A",
                    "isbn": "",
                    "genre": "Tech",
                    "publication_year": 2024,
                    "total_copies": 2,
                    "available_copies": 2,
                    "status": "available",
                }
            ],
        )
        self._write_json(
            members_file,
            members
            or [
                {
                    "member_id": "M001",
                    "name": "Alice",
                    "email": "alice@example.com",
                    "phone": "555",
                    "membership_date": "2026-01-01",
                    "status": "active",
                    "address": {},
                }
            ],
        )
        self._write_json(transactions_file, transactions or [])
        self._write_json(member_books_file, member_books or [])

        service = TransactionService(
            transactions_file=transactions_file,
            books_file=books_file,
            members_file=members_file,
            member_books_file=member_books_file,
        )
        return temp_dir, service, books_file, members_file, transactions_file, member_books_file

    def test_fetch_transactions(self):
        temp_dir, service, _, _, _, _ = self._make_service(
            transactions=[
                {"transaction_id": "T00001", "member_id": "M001", "book_id": "B0001", "status": "borrowed"},
                {"transaction_id": "T00002", "member_id": "M002", "book_id": "B0002", "status": "borrowed"},
            ]
        )
        self.addCleanup(temp_dir.cleanup)

        all_rows = service.fetch_all_transactions()
        selected = service.fetch_previous_transactions("M001", "B0001")

        self.assertEqual(len(all_rows), 2)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["transaction_id"], "T00001")

    def test_borrow_book_adds_transaction_and_updates_inventory_and_member_books(self):
        temp_dir, service, books_file, _, transactions_file, member_books_file = self._make_service()
        self.addCleanup(temp_dir.cleanup)

        borrowed_on = date(2026, 4, 1)
        tx = service.borrow_book("M001", "B0001", borrow_date=borrowed_on)

        self.assertEqual(tx["status"], "borrowed")
        self.assertEqual(tx["borrow_date"], "2026-04-01")
        self.assertEqual(tx["due_date"], "2026-04-16")
        self.assertEqual(tx["max_borrow_days"], MAX_BORROW_DAYS)

        books_after = json.loads(books_file.read_text(encoding="utf-8"))
        self.assertEqual(books_after[0]["available_copies"], 1)

        tx_after = json.loads(transactions_file.read_text(encoding="utf-8"))
        self.assertEqual(len(tx_after), 1)

        member_books_after = json.loads(member_books_file.read_text(encoding="utf-8"))
        self.assertEqual(member_books_after[0]["id"], "M001_B0001")
        self.assertEqual(member_books_after[0]["transaction_ids"], [tx["transaction_id"]])

    def test_borrow_book_blocks_when_member_has_5_active_loans(self):
        books = [
            {
                "book_id": f"B000{i}",
                "title": f"Book {i}",
                "author": "A",
                "isbn": "",
                "genre": "Tech",
                "publication_year": 2024,
                "total_copies": 2,
                "available_copies": 2,
                "status": "available",
            }
            for i in range(1, 7)
        ]
        transactions = [
            {
                "transaction_id": f"T0000{i}",
                "member_id": "M001",
                "book_id": f"B000{i}",
                "borrow_date": "2026-04-01",
                "due_date": "2026-04-16",
                "return_date": None,
                "status": "borrowed",
                "max_borrow_days": 15,
            }
            for i in range(1, 6)
        ]
        temp_dir, service, _, _, _, _ = self._make_service(books=books, transactions=transactions)
        self.addCleanup(temp_dir.cleanup)

        with self.assertRaises(ConflictError):
            service.borrow_book("M001", "B0006", borrow_date=date(2026, 4, 2))

    def test_return_book_on_time_creates_return_transaction(self):
        transactions = [
            {
                "transaction_id": "T00001",
                "member_id": "M001",
                "book_id": "B0001",
                "borrow_date": "2026-04-01",
                "due_date": "2026-04-16",
                "return_date": None,
                "status": "borrowed",
                "max_borrow_days": 15,
            }
        ]
        books = [
            {
                "book_id": "B0001",
                "title": "Book 1",
                "author": "A",
                "isbn": "",
                "genre": "Tech",
                "publication_year": 2024,
                "total_copies": 2,
                "available_copies": 1,
                "status": "issued",
            }
        ]
        member_books = [
            {"id": "M001_B0001", "member_id": "M001", "book_id": "B0001", "transaction_ids": ["T00001"]}
        ]

        temp_dir, service, books_file, _, transactions_file, member_books_file = self._make_service(
            books=books,
            transactions=transactions,
            member_books=member_books,
        )
        self.addCleanup(temp_dir.cleanup)

        tx = service.return_book("M001", "B0001", return_date=date(2026, 4, 10))

        self.assertEqual(tx["status"], "returned")
        self.assertEqual(tx["borrow_transaction_id"], "T00001")
        self.assertFalse(tx["delay_info"]["is_delayed"])
        self.assertEqual(tx["delay_info"]["days_overdue"], 0)
        self.assertIsNone(tx["delay_info"]["return_date_actual"])
        self.assertEqual(tx["delay_info"]["total_fine"], 0.0)

        books_after = json.loads(books_file.read_text(encoding="utf-8"))
        self.assertEqual(books_after[0]["available_copies"], 2)

        tx_after = json.loads(transactions_file.read_text(encoding="utf-8"))
        self.assertEqual(len(tx_after), 2)

        member_books_after = json.loads(member_books_file.read_text(encoding="utf-8"))
        self.assertEqual(member_books_after[0]["transaction_ids"], ["T00001", "T00002"])

    def test_return_book_late_adds_fine(self):
        transactions = [
            {
                "transaction_id": "T00001",
                "member_id": "M001",
                "book_id": "B0001",
                "borrow_date": "2026-04-01",
                "due_date": "2026-04-16",
                "return_date": None,
                "status": "borrowed",
                "max_borrow_days": 15,
            }
        ]
        books = [
            {
                "book_id": "B0001",
                "title": "Book 1",
                "author": "A",
                "isbn": "",
                "genre": "Tech",
                "publication_year": 2024,
                "total_copies": 2,
                "available_copies": 1,
                "status": "issued",
            }
        ]

        temp_dir, service, _, _, _, _ = self._make_service(books=books, transactions=transactions)
        self.addCleanup(temp_dir.cleanup)

        tx = service.return_book("M001", "B0001", return_date=date(2026, 4, 20))

        self.assertTrue(tx["delay_info"]["is_delayed"])
        self.assertEqual(tx["delay_info"]["days_overdue"], 4)
        self.assertEqual(tx["delay_info"]["return_date_actual"], "2026-04-20")
        self.assertEqual(tx["delay_info"]["total_fine"], 20.0)


if __name__ == "__main__":
    unittest.main()

