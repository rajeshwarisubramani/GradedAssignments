from pathlib import Path

from backend.utils.json_io import read_json_list, write_json_list


class TransactionsRepository:
    """Append-only transaction log repository."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def all(self) -> list[dict]:
        return read_json_list(self.file_path)

    def append(self, tx: dict) -> None:
        rows = self.all()
        rows.append(tx)
        write_json_list(self.file_path, rows)

