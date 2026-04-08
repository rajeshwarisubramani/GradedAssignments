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

        active = self._active_loans()
        if book_id in active:
            raise ConflictError("Book is already issued.")

        tx = {
            "tx_id": str(uuid4()),
            "event_type": "BORROW",
            "book_id": book_id,
            "member_id": member_id,
            "timestamp": self._now_iso(),
        }
        self.uow.transactions.append(tx)
        self.uow.books.update(book_id, status="ISSUED")
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
        self.uow.books.update(book_id, status="AVAILABLE")
        return tx

