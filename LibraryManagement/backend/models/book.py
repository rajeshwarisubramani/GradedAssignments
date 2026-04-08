from dataclasses import asdict, dataclass


@dataclass
class Book:
    book_id: str
    title: str
    author: str
    genre: str
    status: str = "AVAILABLE"

    def to_dict(self) -> dict:
        return asdict(self)

