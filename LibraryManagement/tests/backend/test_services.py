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
            service.register_member("m1", "Alice", 20, "alice@example.com")

            service.borrow_book("m1", "b1")
            self.assertEqual(service.list_books()[0]["status"], "ISSUED")

            service.return_book("m1", "b1")
            self.assertEqual(service.list_books()[0]["status"], "AVAILABLE")


if __name__ == "__main__":
    unittest.main()

