from backend.config.settings import BOOKS_FILE, MEMBERS_FILE, TRANSACTIONS_FILE
from backend.repositories.books_repo import BooksRepository
from backend.repositories.members_repo import MembersRepository
from backend.repositories.transactions_repo import TransactionsRepository


class UnitOfWork:
    def __init__(self) -> None:
        self.books = BooksRepository(BOOKS_FILE)
        self.members = MembersRepository(MEMBERS_FILE)
        self.transactions = TransactionsRepository(TRANSACTIONS_FILE)

