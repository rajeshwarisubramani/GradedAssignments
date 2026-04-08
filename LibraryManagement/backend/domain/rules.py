VALID_BOOK_STATUSES = {"AVAILABLE", "ISSUED"}
VALID_EVENT_TYPES = {"BORROW", "RETURN"}


def is_non_empty(value: str) -> bool:
    return bool(value and value.strip())

