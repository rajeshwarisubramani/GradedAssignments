from backend.domain.exceptions import ConflictError, ValidationError
from backend.domain.rules import is_non_empty
from backend.models import Book, Member
from backend.repositories.unit_of_work import UnitOfWork
from backend.services.borrow_return_service import BorrowReturnService
from backend.services.report_service import ReportService


class LibraryService:
    def __init__(self, uow: UnitOfWork | None = None) -> None:
        self.uow = uow or UnitOfWork()
        self.borrow_return = BorrowReturnService(self.uow)
        self.reports = ReportService(self.uow)

    def add_book(self, book_id: str, title: str, author: str, genre: str) -> dict:
        if not all(is_non_empty(v) for v in (book_id, title, author, genre)):
            raise ValidationError("Book fields cannot be empty.")
        if self.uow.books.get(book_id):
            raise ConflictError("Book ID already exists.")

        book = Book(book_id=book_id, title=title, author=author, genre=genre)
        self.uow.books.add(book.to_dict())
        return book.to_dict()

    def register_member(self, member_id: str, name: str, age: int, contact_info: str) -> dict:
        if not all(is_non_empty(v) for v in (member_id, name, contact_info)):
            raise ValidationError("Member fields cannot be empty.")
        if self.uow.members.get(member_id):
            raise ConflictError("Member ID already exists.")

        member = Member(member_id=member_id, name=name, age=int(age), contact_info=contact_info)
        self.uow.members.add(member.to_dict())
        return member.to_dict()

    def list_books(self) -> list[dict]:
        return self.uow.books.all()

    def list_members(self) -> list[dict]:
        return self.uow.members.all()

    def search_books(self, query: str) -> list[dict]:
        needle = query.strip().lower()
        if not needle:
            return []
        return [
            book
            for book in self.uow.books.all()
            if needle in book.get("title", "").lower() or needle in book.get("author", "").lower()
        ]

    def borrow_book(self, member_id: str, book_id: str) -> dict:
        return self.borrow_return.borrow_book(member_id=member_id, book_id=book_id)

    def return_book(self, member_id: str, book_id: str) -> dict:
        return self.borrow_return.return_book(member_id=member_id, book_id=book_id)

    def report_available_books_by_genre(self, genre: str) -> list[dict]:
        return self.reports.available_books_by_genre(genre)

    def report_members_with_borrowed_books(self) -> list[dict]:
        return self.reports.members_with_borrowed_books()

    def report_most_popular_genre(self) -> dict:
        return self.reports.most_popular_genre()

    def report_book_history(self, book_id: str) -> list[dict]:
        return self.reports.book_history(book_id)

    def report_member_history(self, member_id: str) -> list[dict]:
        return self.reports.member_history(member_id)