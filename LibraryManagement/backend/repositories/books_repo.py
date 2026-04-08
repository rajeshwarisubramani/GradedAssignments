from pathlib import Path

from backend.utils.json_io import read_json_list, write_json_list


class BooksRepository:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def all(self) -> list[dict]:
        return read_json_list(self.file_path)

    def get(self, book_id: str) -> dict | None:
        for row in self.all():
            if row.get("book_id") == book_id:
                return row
        return None

    def add(self, book: dict) -> None:
        rows = self.all()
        rows.append(book)
        write_json_list(self.file_path, rows)

    def update(self, book_id: str, **updates: object) -> bool:
        rows = self.all()
        for row in rows:
            if row.get("book_id") == book_id:
                row.update(updates)
                write_json_list(self.file_path, rows)
                return True
        return False

