"""Centralized API route definitions for the frontend service layer."""

from __future__ import annotations

import os

DEFAULT_BASE_URL = os.getenv("LIBRARY_API_BASE_URL", "http://localhost:5000")

API_PATHS = {
    "health": "/health",
    "books": "/books",
    "members": "/members",
    "borrow": "/borrow",
    "return": "/return",
    "reports": {
        "available_by_genre": "/reports/available-by-genre",
        "members_with_borrowed_books": "/reports/members-with-borrowed-books",
        "most_popular_genre": "/reports/most-popular-genre",
        "book_history": "/reports/book-history",
        "member_history": "/reports/member-history",
        "member_active_loans": "/reports/member-active-loans",
    },
}

