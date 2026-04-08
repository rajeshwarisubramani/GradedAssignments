from collections import Counter
from backend.domain.exceptions import NotFoundError, ValidationError

class ReportService:
    def __init__(self, uow) -> None:
        self.uow = uow

    def available_books_by_genre(self, genre: str) -> list[dict]:
        target = genre.strip().lower()
        return [
            b
            for b in self.uow.books.all()
            if b.get("status") == "AVAILABLE" and b.get("genre", "").lower() == target
        ]

    def members_with_borrowed_books(self) -> list[dict]:
        active: dict[str, str] = {}
        for tx in self.uow.transactions.all():
            book_id = tx["book_id"]
            if tx["event_type"] == "BORROW":
                active[book_id] = tx["member_id"]
            elif tx["event_type"] == "RETURN":
                active.pop(book_id, None)

        borrowed_by_member: dict[str, list[str]] = {}
        for book_id, member_id in active.items():
            borrowed_by_member.setdefault(member_id, []).append(book_id)

        result = []
        for member in self.uow.members.all():
            member_id = member["member_id"]
            books = borrowed_by_member.get(member_id, [])
            if books:
                result.append({"member": member, "borrowed_book_ids": books})
        return result

    def most_popular_genre(self) -> dict:
        books = {b["book_id"]: b for b in self.uow.books.all()}
        counter: Counter[str] = Counter()
        for tx in self.uow.transactions.all():
            if tx.get("event_type") != "BORROW":
                continue
            book = books.get(tx.get("book_id"))
            if book:
                counter[book.get("genre", "Unknown")] += 1

        if not counter:
            return {"genre": None, "count": 0}

        genre, count = counter.most_common(1)[0]
        return {"genre": genre, "count": count}

    def book_history(self, book_id: str) -> list[dict]:
        normalized = book_id.strip()
        if not normalized:
            raise ValidationError("book_id is required.")
        if not self.uow.books.get(normalized):
            raise NotFoundError("Book not found.")

        return [tx for tx in self.uow.transactions.all() if tx.get("book_id") == normalized]

    def member_history(self, member_id: str) -> list[dict]:
        normalized = member_id.strip()
        if not normalized:
            raise ValidationError("member_id is required.")
        if not self.uow.members.get(normalized):
            raise NotFoundError("Member not found.")

        return [tx for tx in self.uow.transactions.all() if tx.get("member_id") == normalized]
