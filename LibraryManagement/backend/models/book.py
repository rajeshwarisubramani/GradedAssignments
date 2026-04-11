from dataclasses import asdict, dataclass


@dataclass
class Book:
    book_id: str
    title: str
    author: str
    genre: str
    isbn: str = ""
    publication_year: int | None = None
    total_copies: int = 1
    available_copies: int = 1
    status: str = "available"

    def __post_init__(self) -> None:
        self.total_copies = max(1, int(self.total_copies))
        self.available_copies = max(0, min(int(self.available_copies), self.total_copies))

        if self.publication_year in ("", None):
            self.publication_year = None
        else:
            self.publication_year = int(self.publication_year)

        self.status = (self.status or "available").lower()

    def to_dict(self) -> dict:
        return asdict(self)

