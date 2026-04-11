from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.domain.exceptions import ConflictError, NotFoundError


class BorrowReturnService:
    def __init__(self, uow) -> None:
        self.uow = uow

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _active_loans(self) -> dict[str, str]:
        active: dict[str, str] = {}
        for tx in self.uow.transactions.all():
            book_id = tx["book_id"]
            if tx["event_type"] == "BORROW":
                active[book_id] = tx["member_id"]
            elif tx["event_type"] == "RETURN":
                active.pop(book_id, None)
        return active

    def borrow_book(self, member_id: str, book_id: str) -> dict:
        member = self.uow.members.get(member_id)
        if not member:
            raise NotFoundError("Member not found.")

        book = self.uow.books.get(book_id)
        if not book:
            raise NotFoundError("Book not found.")

        available_copies = int(book.get("available_copies", 1))
        if available_copies <= 0:
            raise ConflictError("Book is already issued.")

        tx = {
            "tx_id": str(uuid4()),
            "event_type": "BORROW",
            "book_id": book_id,
            "member_id": member_id,
            "timestamp": self._now_iso(),
        }
        self.uow.transactions.append(tx)
        new_available = max(0, available_copies - 1)
        new_status = "issued" if new_available == 0 else "available"
        self.uow.books.update(book_id, available_copies=new_available, status=new_status)
        return tx

    def return_book(self, member_id: str, book_id: str) -> dict:
        member = self.uow.members.get(member_id)
        if not member:
            raise NotFoundError("Member not found.")

        book = self.uow.books.get(book_id)
        if not book:
            raise NotFoundError("Book not found.")

        active = self._active_loans()
        if active.get(book_id) != member_id:
            raise ConflictError("This member does not have this book issued.")

        tx = {
            "tx_id": str(uuid4()),
            "event_type": "RETURN",
            "book_id": book_id,
            "member_id": member_id,
            "timestamp": self._now_iso(),
        }
        self.uow.transactions.append(tx)
        total_copies = int(book.get("total_copies", 1))
        available_copies = int(book.get("available_copies", 0))
        new_available = min(total_copies, available_copies + 1)
        self.uow.books.update(book_id, available_copies=new_available, status="available")
        return tx

