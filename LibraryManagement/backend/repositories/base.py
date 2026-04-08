from typing import Protocol


class Repository(Protocol):
    def all(self) -> list[dict]:
        ...

