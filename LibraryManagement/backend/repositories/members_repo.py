from pathlib import Path

from backend.utils.json_io import read_json_list, write_json_list


class MembersRepository:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def all(self) -> list[dict]:
        return read_json_list(self.file_path)

    def get(self, member_id: str) -> dict | None:
        for row in self.all():
            if row.get("member_id") == member_id:
                return row
        return None

    def add(self, member: dict) -> None:
        rows = self.all()
        rows.append(member)
        write_json_list(self.file_path, rows)

    def find_by_name(self, name_query: str) -> list[dict]:
        needle = name_query.strip().lower()
        if not needle:
            return []

        return [
            member
            for member in self.all()
            if needle in str(member.get("name", "")).lower()
        ]

