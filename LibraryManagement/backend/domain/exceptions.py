class LibraryError(Exception):
    """Base domain exception."""


class ValidationError(LibraryError):
    """Raised when input data is invalid."""


class NotFoundError(LibraryError):
    """Raised when a requested record is missing."""


class ConflictError(LibraryError):
    """Raised when operation violates current state."""

