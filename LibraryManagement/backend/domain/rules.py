VALID_BOOK_STATUSES = {"available", "issued"}
VALID_EVENT_TYPES = {"BORROW", "RETURN"}


def is_non_empty(value: str) -> bool:
    return bool(value and value.strip())

