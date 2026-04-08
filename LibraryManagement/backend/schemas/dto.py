from typing import TypedDict


class MessageDTO(TypedDict):
    message: str


class PopularGenreDTO(TypedDict):
    genre: str | None
    count: int

