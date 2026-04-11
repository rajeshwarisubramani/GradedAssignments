import json
import tempfile
import unittest
from pathlib import Path

from backend.services.book_service import BookService


class BookServiceTests(unittest.TestCase):
    def _make_service(self) -> tuple[tempfile.TemporaryDirectory, Path, BookService]:
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        books_file = root / "books.json"
        books_file.write_text(
            json.dumps(
                [
                    {
                        "book_id": "B0001",
                        "title": "Python Programming",
                        "author": "John Smith",
                        "isbn": "978-0-123456-78-9",
                        "genre": "Technology",
                        "publication_year": 2020,
                        "total_copies": 5,
                        "available_copies": 4,
                        "status": "available",
                    },
                    {
                        "book_id": "B0002",
                        "title": "Python Programming",
                        "author": "Someone Else",
                        "isbn": "",
                        "genre": "Technology",
                        "publication_year": 2020,
                        "total_copies": 1,
                        "available_copies": 1,
                        "status": "available",
                    },
                ]
            ),
            encoding="utf-8",
        )
        return temp_dir, books_file, BookService(file_path=books_file)

    def test_fetch_all_books(self):
        temp_dir, _, service = self._make_service()
        self.addCleanup(temp_dir.cleanup)

        books = service.fetch_all_books()

        self.assertEqual(len(books), 2)

    def test_fetch_books_by_name_returns_array(self):
        temp_dir, _, service = self._make_service()
        self.addCleanup(temp_dir.cleanup)

        books = service.fetch_books_by_name("python programming")

        self.assertEqual(len(books), 2)

    def test_fetch_book_by_id(self):
        temp_dir, _, service = self._make_service()
        self.addCleanup(temp_dir.cleanup)

        book = service.fetch_book_by_id("B0001")

        self.assertIsNotNone(book)
        self.assertEqual(book["isbn"], "978-0-123456-78-9")

    def test_add_book_with_isbn_increases_existing_copies(self):
        temp_dir, _, service = self._make_service()
        self.addCleanup(temp_dir.cleanup)

        updated = service.add_book(
            title="Different Title",
            author="Another Author",
            genre="Technology",
            publication_year=2024,
            isbn="978-0-123456-78-9",
            copies=2,
        )

        self.assertEqual(updated["book_id"], "B0001")
        self.assertEqual(updated["total_copies"], 7)
        self.assertEqual(updated["available_copies"], 6)

    def test_add_book_without_isbn_matches_title_and_year(self):
        temp_dir, _, service = self._make_service()
        self.addCleanup(temp_dir.cleanup)

        updated = service.add_book(
            title="Python Programming",
            author="Any",
            genre="Technology",
            publication_year=2020,
            isbn="",
            copies=3,
        )

        self.assertEqual(updated["book_id"], "B0001")
        self.assertEqual(updated["total_copies"], 8)
        self.assertEqual(updated["available_copies"], 7)

    def test_add_book_creates_new_row_when_no_match(self):
        temp_dir, _, service = self._make_service()
        self.addCleanup(temp_dir.cleanup)

        created = service.add_book(
            title="New Book",
            author="New Author",
            genre="Adventure",
            publication_year=2022,
            isbn="978-1-111111-11-1",
            copies=2,
        )

        self.assertEqual(created["book_id"], "B0003")
        self.assertEqual(created["total_copies"], 2)
        self.assertEqual(created["available_copies"], 2)

    def test_update_available_copies_on_return(self):
        temp_dir, _, service = self._make_service()
        self.addCleanup(temp_dir.cleanup)

        updated = service.update_available_copies_on_return("B0001", returned_copies=3)

        self.assertEqual(updated["available_copies"], 5)
        self.assertEqual(updated["status"], "available")


if __name__ == "__main__":
    unittest.main()

