import tempfile
import unittest
from pathlib import Path

from backend.repositories.books_repo import BooksRepository
from backend.repositories.members_repo import MembersRepository
from backend.repositories.transactions_repo import TransactionsRepository
from backend.services.library_service import LibraryService


class InMemoryUow:
    def __init__(self, root: Path) -> None:
        self.books = BooksRepository(root / "books.json")
        self.members = MembersRepository(root / "members.json")
        self.transactions = TransactionsRepository(root / "transactions.json")


class LibraryServiceTests(unittest.TestCase):
    def test_borrow_and_return(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("books.json", "members.json", "transactions.json"):
                (root / name).write_text("[]", encoding="utf-8")

            service = LibraryService(uow=InMemoryUow(root))
            service.add_book("b1", "Book One", "Author", "Sci-Fi")
            service.register_member("m1", "Alice", "alice@example.com", "555-0001", "2024-01-15")

            service.borrow_book("m1", "b1")
            self.assertEqual(service.list_books()[0]["status"], "issued")

            service.return_book("m1", "b1")
            self.assertEqual(service.list_books()[0]["status"], "available")

    def test_report_member_active_loans(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("books.json", "members.json", "transactions.json"):
                (root / name).write_text("[]", encoding="utf-8")

            service = LibraryService(uow=InMemoryUow(root))
            service.add_book("b1", "Book One", "Author A", "Sci-Fi")
            service.add_book("b2", "Book Two", "Author B", "History")
            service.register_member("m1", "Alice", "alice@example.com", "555-0001", "2024-01-15")

            service.borrow_book("m1", "b1")
            service.borrow_book("m1", "b2")
            service.return_book("m1", "b1")

            active = service.report_member_active_loans("m1")

            self.assertEqual(len(active), 1)
            self.assertEqual(active[0]["book"]["book_id"], "b2")

    def test_search_members_by_incomplete_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("books.json", "members.json", "transactions.json"):
                (root / name).write_text("[]", encoding="utf-8")

            service = LibraryService(uow=InMemoryUow(root))
            service.register_member("m1", "Alice Johnson", "alice@example.com", "555-0001", "2024-01-15")
            service.register_member("m2", "Bob Stone", "bob@example.com", "555-0002", "2024-01-16")
            service.register_member("m3", "Alicia Keys", "alicia@example.com", "555-0003", "2024-01-17")

            results = service.search_members("ali")

            self.assertEqual(len(results), 2)
            member_ids = {member["member_id"] for member in results}
            self.assertEqual(member_ids, {"m1", "m3"})


if __name__ == "__main__":
    unittest.main()

