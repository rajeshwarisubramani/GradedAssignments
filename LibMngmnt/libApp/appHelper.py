"""
Library Management System - Helper Functions
=============================================
This module contains all business logic, I/O operations, and utility functions.
"""

import json
import os
from datetime import date, datetime, timedelta

# ─────────────────────────────────────────────────────────────
# FILE PATHS & CONSTANTS
# ─────────────────────────────────────────────────────────────
BOOKS_FILE        = "books.json"
MEMBERS_FILE      = "members.json"
TRANSACTIONS_FILE = "transactions.json"
MEMBER_BOOKS_FILE = "member_books.json"

FINE_PER_DAY    = 5.00   # ₹ per overdue day
MAX_BORROW_DAYS = 15
MAX_ACTIVE_BORROWS = 3


# ═════════════════════════════════════════════════════════════
# SECTION 1 ── I/O HELPERS
# ═════════════════════════════════════════════════════════════

def load_json(path: str, default):
    """Load JSON from *path*; return *default* if file is absent."""
    if os.path.exists(path):
        with open(path, "r") as fh:
            return json.load(fh)
    return default


def save_json(path: str, data) -> None:
    """Persist *data* as pretty-printed JSON to *path*."""
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)


def load_all():
    """Return all four data collections as a tuple."""
    books        = load_json(BOOKS_FILE,        [])
    members      = load_json(MEMBERS_FILE,      [])
    transactions = load_json(TRANSACTIONS_FILE, [])
    member_books = load_json(MEMBER_BOOKS_FILE, [])
    return books, members, transactions, member_books


def save_all(books, members, transactions, member_books) -> None:
    """Persist all four collections to disk."""
    save_json(BOOKS_FILE,        books)
    save_json(MEMBERS_FILE,      members)
    save_json(TRANSACTIONS_FILE, transactions)
    save_json(MEMBER_BOOKS_FILE, member_books)


# ═════════════════════════════════════════════════════════════
# SECTION 2 ── ID GENERATORS
# ═════════════════════════════════════════════════════════════

def next_book_id(books: list) -> str:
    """Generate the next sequential book ID, e.g. B0013."""
    if not books:
        return "B0001"
    nums = [int(b["book_id"][1:]) for b in books if b.get("book_id", "").startswith("B")]
    return f"B{max(nums) + 1:04d}"


def next_member_id(members: list) -> str:
    """Generate the next sequential member ID, e.g. M0004."""
    if not members:
        return "M0001"
    nums = [int(m["member_id"][1:]) for m in members if m.get("member_id", "").startswith("M")]
    return f"M{max(nums) + 1:04d}"


def next_transaction_id(transactions: list) -> str:
    """Generate the next sequential transaction ID, e.g. T00005."""
    if not transactions:
        return "T00001"
    nums = [int(t["transaction_id"][1:]) for t in transactions if t.get("transaction_id", "").startswith("T")]
    return f"T{max(nums) + 1:05d}"


# ═════════════════════════════════════════════════════════════
# SECTION 3 ── LOOKUP HELPERS
# ═════════════════════════════════════════════════════════════

def find_book(books: list, book_id: str) -> dict | None:
    """Return the book dict matching *book_id*, or None."""
    for b in books:
        if b["book_id"] == book_id:
            return b
    return None


def find_member(members: list, member_id: str) -> dict | None:
    """Return the member dict matching *member_id*, or None."""
    for m in members:
        if m["member_id"] == member_id:
            return m
    return None


def find_transaction(transactions: list, transaction_id: str) -> dict | None:
    """Return the transaction dict matching *transaction_id*, or None."""
    for t in transactions:
        if t["transaction_id"] == transaction_id:
            return t
    return None


def find_member_book(member_books: list, member_id: str, book_id: str) -> dict | None:
    """Return the member_books link for a member–book pair, or None."""
    for mb in member_books:
        if mb["member_id"] == member_id and mb["book_id"] == book_id:
            return mb
    return None


def get_active_borrow(transactions: list, member_id: str, book_id: str) -> dict | None:
    """
    Return the open borrow transaction for a member/book pair, or None.
    An open borrow has status == 'borrowed' and no borrow_transaction_id
    (i.e. it is the original borrow record, not a return record).
    """
    for t in transactions:
        if (
            t["member_id"] == member_id
            and t["book_id"]   == book_id
            and t["status"]    == "borrowed"
            and "borrow_transaction_id" not in t
        ):
            return t
    return None


# ═════════════════════════════════════════════════════════════
# SECTION 4 ── CORE BUSINESS LOGIC
# ═════════════════════════════════════════════════════════════

def add_book(
    books: list,
    title: str,
    author: str,
    isbn: str,
    genre: str,
    publication_year: int,
    total_copies: int,
) -> tuple:
    """
    Add a new book to *books*.

    Returns (success: bool, message: str, updated_books: list).
    Rejects duplicates based on ISBN.
    """
    isbn = isbn.strip()
    if any(b["isbn"] == isbn for b in books):
        return False, f"A book with ISBN '{isbn}' already exists.", books

    book_id  = next_book_id(books)
    new_book = {
        "book_id":          book_id,
        "title":            title.strip(),
        "author":           author.strip(),
        "isbn":             isbn,
        "genre":            genre.strip(),
        "publication_year": int(publication_year),
        "total_copies":     int(total_copies),
        "available_copies": int(total_copies),
        "status":           "available",
    }
    books.append(new_book)
    return True, f"Book added with ID **{book_id}**.", books


def register_member(
    members: list,
    name: str,
    email: str,
    phone: str,
    street: str,
    city: str,
    postal_code: str,
) -> tuple:
    """
    Register a new library member.

    Returns (success: bool, message: str, updated_members: list).
    Rejects duplicate e-mail addresses.
    """
    email = email.strip().lower()
    if any(m["email"].lower() == email for m in members):
        return False, f"A member with e-mail '{email}' is already registered.", members

    member_id  = next_member_id(members)
    new_member = {
        "member_id":       member_id,
        "name":            name.strip(),
        "email":           email,
        "phone":           phone.strip(),
        "membership_date": str(date.today()),
        "status":          "active",
        "address": {
            "street":      street.strip(),
            "city":        city.strip(),
            "postal_code": postal_code.strip(),
        },
    }
    members.append(new_member)
    return True, f"Member registered with ID **{member_id}**.", members


def borrow_book(
    books: list,
    members: list,
    transactions: list,
    member_books: list,
    book_id: str,
    member_id: str,
    borrow_date: date,
) -> tuple:
    """
    Record a book borrow.

    Business rules enforced:
    - Book must exist and have available copies.
    - Member must exist and be active.
    - Member can have at most 3 active borrowed books.
    - Member must not already have this exact book borrowed.

    Returns (success, message, books, members, transactions, member_books).
    """
    book = find_book(books, book_id)
    if not book:
        return False, f"Book {book_id} not found.", books, members, transactions, member_books

    member = find_member(members, member_id)

    if not member:
        return False, f"Member {member_id} not found.", books, members, transactions, member_books

    if member["status"] != "active":
        return False, "Member account is not active.", books, members, transactions, member_books

    open_member_borrows = get_open_member_borrows(transactions, member_id)

    if len(open_member_borrows)  >= MAX_ACTIVE_BORROWS:
        return False, f"Member already has {MAX_ACTIVE_BORROWS} active borrows.", books, members, transactions, member_books

    if book["available_copies"] <= 0:
        return False, f"No copies of '{book['title']}' are currently available.", books, members, transactions, member_books

    if get_active_borrow(transactions, member_id, book_id):
        return False, "This member already has this book borrowed.", books, members, transactions, member_books

    due_date = borrow_date + timedelta(days=MAX_BORROW_DAYS)
    txn_id   = next_transaction_id(transactions)

    new_txn = {
        "transaction_id":  txn_id,
        "member_id":       member_id,
        "book_id":         book_id,
        "borrow_date":     str(borrow_date),
        "due_date":        str(due_date),
        "return_date":     None,
        "status":          "borrowed",
        "max_borrow_days": MAX_BORROW_DAYS,
    }
    transactions.append(new_txn)

    # Update available copies and book status
    book["available_copies"] -= 1
    if book["available_copies"] == 0:
        book["status"] = "unavailable"

    # Update or create the member_books link
    mb = find_member_book(member_books, member_id, book_id)
    if mb:
        mb["transaction_ids"].append(txn_id)
    else:
        member_books.append({
            "id":              f"{member_id}_{book_id}",
            "member_id":       member_id,
            "book_id":         book_id,
            "transaction_ids": [txn_id],
        })
    msg = (
        f"**'{book['title']}'** borrowed by **{member['name']}**.\n\n"
        f"Transaction ID: **{txn_id}** | Due date: **{due_date}**"
    )
    return True, msg, books, members, transactions, member_books


def calculate_fine(due_date_str: str, return_date_str: str) -> dict:
    """
    Compute overdue fine information given due date and actual return date.

    Returns a delay_info dict matching the transactions.json schema.
    """
    due          = datetime.strptime(due_date_str,    "%Y-%m-%d").date()
    ret          = datetime.strptime(return_date_str, "%Y-%m-%d").date()
    overdue_days = max(0, (ret - due).days)
    fine         = round(overdue_days * FINE_PER_DAY, 2)
    return {
        "is_delayed":         overdue_days > 0,
        "days_overdue":       overdue_days,
        "return_date_actual": return_date_str if overdue_days > 0 else None,
        "fine_per_day":       FINE_PER_DAY,
        "total_fine":         fine,
    }


def return_book(
    books: list,
    transactions: list,
    member_books: list,
    borrow_txn_id: str,
    return_date: date,
) -> tuple:
    """
    Record a book return.

    Creates a new return-transaction that references the original borrow —
    matching the two-record pattern in transactions.json (T00001 / T00002).
    Also marks the original borrow transaction as returned.

    Returns (success, message, delay_info, books, transactions, member_books).
    """
    borrow_txn = find_transaction(transactions, borrow_txn_id)
    if not borrow_txn:
        return False, f"Transaction {borrow_txn_id} not found.", {}, books, transactions, member_books

    if borrow_txn["status"] != "borrowed" or "borrow_transaction_id" in borrow_txn:
        return False, "This transaction is not an open borrow.", {}, books, transactions, member_books

    delay_info = calculate_fine(borrow_txn["due_date"], str(return_date))
    ret_txn_id = next_transaction_id(transactions)

    return_txn = {
        "transaction_id":        ret_txn_id,
        "borrow_transaction_id": borrow_txn_id,
        "member_id":             borrow_txn["member_id"],
        "book_id":               borrow_txn["book_id"],
        "borrow_date":           borrow_txn["borrow_date"],
        "due_date":              borrow_txn["due_date"],
        "return_date":           str(return_date),
        "status":                "returned",
        "max_borrow_days":       MAX_BORROW_DAYS,
        "delay_info":            delay_info,
    }
    transactions.append(return_txn)

    book = find_book(books, borrow_txn["book_id"])
    if not book:
        return False, f"Book {borrow_txn["book_id"]} not found.", books, transactions, member_books
    total = int(book.get("total_copies", 0))
    available = int(book.get("available_copies", 0))
    if (total == available):
        msg = (
            f"**'{book['title']}'** is never borrowed.\n\n"
        )
    book["available_copies"]  = available + 1

    # Append return transaction id to member_books
    mb = find_member_book(member_books, borrow_txn["member_id"], borrow_txn["book_id"])
    if mb:
        mb["transaction_ids"].append(ret_txn_id)

    fine_msg = (
        f"⚠️ Overdue by **{delay_info['days_overdue']}** day(s). Fine: **₹{delay_info['total_fine']:.2f}**"
        if delay_info["is_delayed"]
        else "✅ Returned on time. No fine."
    )
    msg = f"Book returned. Return Txn ID: **{ret_txn_id}**\n\n{fine_msg}"
    return True, msg, delay_info, books, transactions, member_books


def update_book_availability(book_id: str, action: str) -> tuple:
    """
    Update available_copies and status in books.json for a given book_id.

    Args:
        book_id: e.g. "B0001"
        action: "borrowed" or "returned"

    Returns:
        (success: bool, message: str, updated_book: dict | None)
    """
    action = action.strip().lower()
    if action not in {"borrowed", "returned"}:
        return False, "action must be 'borrowed' or 'returned'.", None

    books = load_json(BOOKS_FILE, [])
    book = find_book(books, book_id)
    if not book:
        return False, f"Book {book_id} not found.", None

    total = int(book.get("total_copies", 0))
    available = int(book.get("available_copies", 0))

    if action == "borrowed":
        if available <= 0:
            return False, "No copies available to borrow.", None
        book["available_copies"] = available - 1
        if book["available_copies"] == 0:
            book["status"] = "unavailable"
        ok = True
    else:  # action == "returned"
        if available >= total:
            return False, "All copies are already available; cannot return.", None
        book["available_copies"] = available + 1
        if book["available_copies"] > 0:
            book["status"] = "available"
        ok = True

    save_json(BOOKS_FILE, books)
    return ok, "Book availability updated.", book


# ═════════════════════════════════════════════════════════════
# SECTION 5 ── REPORT HELPERS
# ═════════════════════════════════════════════════════════════

def get_open_borrow_transactions(transactions: list[dict]) -> list[dict]:
    """
    Return borrowed transaction objects that are NOT referenced in any
    transaction's borrow_transaction_id.
    """
    referenced_borrow_ids = {
        t.get("borrow_transaction_id")
        for t in transactions
        if t.get("borrow_transaction_id")
    }

    return [
        t
        for t in transactions
        if t.get("status") == "borrowed"
        and t.get("transaction_id") not in referenced_borrow_ids
    ]


def get_open_member_borrows(transactions: list[dict], member_id: str) -> list[dict]:
    """
    Return borrowed transaction objects for a specific member that are NOT
    referenced in any transaction's borrow_transaction_id field.

    Args:
        transactions: List of all transactions
        member_id: The member ID to filter by

    Returns:
        List of open borrow transaction dicts for this member
    """
    referenced_borrow_ids = {
        t.get("borrow_transaction_id")
        for t in transactions
        if t.get("borrow_transaction_id")
    }

    return [
        t
        for t in transactions
        if (
                t.get("member_id") == member_id
                and t.get("status") == "borrowed"
                and t.get("transaction_id") not in referenced_borrow_ids
        )
    ]


def get_open_borrows(transactions: list) -> list:
    """Return all transactions that are open borrows (not yet returned)."""
    return [
        t for t in transactions
        if t["status"] == "borrowed" and "borrow_transaction_id" not in t
    ]

def get_open_member_borrows_overdue(transactions: list[dict], member_id: str) -> list[dict]:
    """
    Return borrowed transaction objects for a specific member that:
    - Have status == 'borrowed'
    - Are NOT referenced by any transaction's borrow_transaction_id (no return record exists)
    - Have due_date < today
    """
    referenced_borrow_ids = {
        t.get("borrow_transaction_id")
        for t in transactions
        if t.get("borrow_transaction_id")
    }

    result = []
    for t in transactions:
        if (
            t.get("member_id") == member_id
            and t.get("status") == "borrowed"
            and t.get("transaction_id") not in referenced_borrow_ids
        ):
            try:
                due_date = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
                if due_date < date.today():
                    result.append(t)
            except (ValueError, TypeError, KeyError):
                pass

    return result

def get_open_overdue_borrow_transactions(transactions: list[dict]) -> list[dict]:
    """
    Return borrowed transaction objects that:
    - Have status == 'borrowed'
    - Are NOT referenced by any transaction's borrow_transaction_id (no return record exists)
    - Have due_date < today
    """
    referenced_borrow_ids = {
        t.get("borrow_transaction_id")
        for t in transactions
        if t.get("borrow_transaction_id")
    }

    result = []
    today = date.today()

    for t in transactions:
        if (
            t.get("status") == "borrowed"
            and t.get("transaction_id") not in referenced_borrow_ids
        ):
            try:
                due_date = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
                if due_date < today:
                    result.append(t)
            except (ValueError, TypeError, KeyError):
                pass

    return result

def get_overdue_borrows(transactions: list) -> list:
    """Return open borrows whose due date has already passed."""
    today  = date.today()
    result = []
    for t in get_open_borrows(transactions):
        due = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
        if due < today:
            result.append(t)
    return result


def get_member_history(transactions: list, member_id: str) -> list:
    """Return all original borrow transactions for a given member."""
    return [
        t for t in transactions
        if t["member_id"] == member_id and "borrow_transaction_id" not in t
    ]


def total_fines_collected(transactions: list) -> float:
    """Sum all fines from completed return transactions."""
    today = date.today()
    total = 0.0
    for t in transactions:
        due = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
        overdue = (today - due).days
        is_overdue = overdue > 0
        fine = round(overdue * FINE_PER_DAY, 2) if is_overdue else 0.0
        total += fine
    return round(total, 2)

