"""
Library Management System
=========================
Data files  : books.json, members.json, transactions.json, member_books.json
Run         : streamlit run library_app.py
"""

import json
import os
import streamlit as st
from datetime import date, datetime, timedelta

# ─────────────────────────────────────────────────────────────
# FILE PATHS
# ─────────────────────────────────────────────────────────────
BOOKS_FILE        = "books.json"
MEMBERS_FILE      = "members.json"
TRANSACTIONS_FILE = "transactions.json"
MEMBER_BOOKS_FILE = "member_books.json"

FINE_PER_DAY    = 5.00   # ₹ per overdue day
MAX_BORROW_DAYS = 15


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

    # Close the original borrow record
    borrow_txn["status"]      = "returned"
    borrow_txn["return_date"] = str(return_date)

    # Restore available copy count
    book = find_book(books, borrow_txn["book_id"])
    if book:
        book["available_copies"] += 1
        book["status"] = "available"

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


# ═════════════════════════════════════════════════════════════
# SECTION 5 ── REPORT HELPERS
# ═════════════════════════════════════════════════════════════

def get_open_borrows(transactions: list) -> list:
    """Return all transactions that are open borrows (not yet returned)."""
    return [
        t for t in transactions
        if t["status"] == "borrowed" and "borrow_transaction_id" not in t
    ]


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
    total = 0.0
    for t in transactions:
        if t.get("status") == "returned" and "delay_info" in t:
            total += t["delay_info"].get("total_fine", 0.0)
    return round(total, 2)


# ═════════════════════════════════════════════════════════════
# SECTION 6 ── STREAMLIT UI
# ═════════════════════════════════════════════════════════════

st.set_page_config(page_title="Library Management System", page_icon="📚", layout="wide")
st.title("📚 Library Management System")

# Load once per script run
books, members, transactions, member_books = load_all()

tab_add_book, tab_add_member, tab_borrow, tab_return, tab_reports = st.tabs([
    "➕ Add Book",
    "👤 Register Member",
    "📤 Borrow Book",
    "📥 Return Book",
    "📊 Reports",
])


# ─────────────────────────────────────────────────────────────
# TAB 1 – ADD BOOK
# ─────────────────────────────────────────────────────────────
with tab_add_book:
    st.header("Add a New Book")

    with st.form("form_add_book"):
        c1, c2 = st.columns(2)
        title            = c1.text_input("Title *")
        author           = c2.text_input("Author *")
        isbn             = c1.text_input("ISBN *")
        genre            = c2.text_input("Genre")
        publication_year = c1.number_input(
            "Publication Year", min_value=1000,
            max_value=date.today().year, value=2020, step=1
        )
        total_copies = c2.number_input("Number of Copies", min_value=1, value=1, step=1)
        submitted    = st.form_submit_button("Add Book")

    if submitted:
        if not title.strip() or not author.strip() or not isbn.strip():
            st.error("Title, Author and ISBN are required fields.")
        else:
            ok, msg, books = add_book(
                books, title, author, isbn, genre,
                int(publication_year), int(total_copies)
            )
            if ok:
                save_json(BOOKS_FILE, books)
                st.success(msg)
            else:
                st.error(msg)

    st.divider()
    st.subheader("Current Book Catalogue")
    if books:
        st.dataframe(
            [
                {
                    "ID": b["book_id"], "Title": b["title"], "Author": b["author"],
                    "ISBN": b["isbn"], "Genre": b["genre"],
                    "Year": b["publication_year"],
                    "Total": b["total_copies"], "Available": b["available_copies"],
                    "Status": b["status"].capitalize(),
                }
                for b in books
            ],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No books in the catalogue yet.")


# ─────────────────────────────────────────────────────────────
# TAB 2 – REGISTER MEMBER
# ─────────────────────────────────────────────────────────────
with tab_add_member:
    st.header("Register a New Member")

    with st.form("form_add_member"):
        c1, c2 = st.columns(2)
        name  = c1.text_input("Full Name *")
        email = c2.text_input("E-mail *")
        phone = c1.text_input("Phone")
        st.caption("Address (optional)")
        ca1, ca2, ca3 = st.columns(3)
        street      = ca1.text_input("Street")
        city        = ca2.text_input("City")
        postal_code = ca3.text_input("Postal Code")
        submitted2  = st.form_submit_button("Register Member")

    if submitted2:
        if not name.strip() or not email.strip():
            st.error("Name and E-mail are required fields.")
        else:
            ok, msg, members = register_member(
                members, name, email, phone, street, city, postal_code
            )
            if ok:
                save_json(MEMBERS_FILE, members)
                st.success(msg)
            else:
                st.error(msg)

    st.divider()
    st.subheader("Registered Members")
    if members:
        st.dataframe(
            [
                {
                    "ID": m["member_id"], "Name": m["name"], "E-mail": m["email"],
                    "Phone": m["phone"], "Member Since": m["membership_date"],
                    "Status": m["status"].capitalize(),
                }
                for m in members
            ],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No members registered yet.")


# ─────────────────────────────────────────────────────────────
# TAB 3 – BORROW BOOK
# ─────────────────────────────────────────────────────────────
with tab_borrow:
    st.header("Borrow a Book")

    available_books = [b for b in books if b["available_copies"] > 0]
    active_members  = [m for m in members if m["status"] == "active"]

    if not available_books:
        st.warning("No books are currently available for borrowing.")
    elif not active_members:
        st.warning("No active members found. Please register a member first.")
    else:
        book_options = {
            f"{b['title']} — {b['author']} (ID: {b['book_id']}, Available: {b['available_copies']})": b["book_id"]
            for b in available_books
        }
        member_options = {
            f"{m['name']} (ID: {m['member_id']})": m["member_id"]
            for m in active_members
        }

        with st.form("form_borrow"):
            sel_book   = st.selectbox("Select Book *",   list(book_options.keys()))
            sel_member = st.selectbox("Select Member *", list(member_options.keys()))
            borrow_dt  = st.date_input("Borrow Date", value=date.today())
            st.caption(f"Due date will be set to {MAX_BORROW_DAYS} days from borrow date.")
            submitted3 = st.form_submit_button("Borrow Book")

        if submitted3:
            bid = book_options[sel_book]
            mid = member_options[sel_member]
            ok, msg, books, members, transactions, member_books = borrow_book(
                books, members, transactions, member_books, bid, mid, borrow_dt
            )
            if ok:
                save_all(books, members, transactions, member_books)
                st.success(msg)
            else:
                st.error(msg)

    st.divider()
    st.subheader("Currently Borrowed Books")
    open_borrows = get_open_borrows(transactions)
    if open_borrows:
        rows = []
        for t in open_borrows:
            b       = find_book(books, t["book_id"])
            m       = find_member(members, t["member_id"])
            due     = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
            overdue = max(0, (date.today() - due).days)
            rows.append({
                "Txn ID":       t["transaction_id"],
                "Book":         b["title"] if b else t["book_id"],
                "Member":       m["name"]  if m else t["member_id"],
                "Borrow Date":  t["borrow_date"],
                "Due Date":     t["due_date"],
                "Days Overdue": overdue if overdue > 0 else "—",
                "Accrued Fine ₹": round(overdue * FINE_PER_DAY, 2) if overdue > 0 else "—",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No books are currently borrowed.")


# ─────────────────────────────────────────────────────────────
# TAB 4 – RETURN BOOK
# ─────────────────────────────────────────────────────────────
with tab_return:
    st.header("Return a Book")

    open_borrows = get_open_borrows(transactions)

    if not open_borrows:
        st.info("No books are currently borrowed.")
    else:
        loan_options = {}
        for t in open_borrows:
            b     = find_book(books, t["book_id"])
            m     = find_member(members, t["member_id"])
            label = (
                f"[{t['transaction_id']}]  "
                f"{b['title'] if b else t['book_id']}  →  "
                f"{m['name']  if m else t['member_id']}  "
                f"(due {t['due_date']})"
            )
            loan_options[label] = t["transaction_id"]

        with st.form("form_return"):
            sel_loan   = st.selectbox("Select Active Loan *", list(loan_options.keys()))
            return_dt  = st.date_input("Return Date", value=date.today())
            submitted4 = st.form_submit_button("Return Book")

        if submitted4:
            txn_id = loan_options[sel_loan]
            ok, msg, delay_info, books, transactions, member_books = return_book(
                books, transactions, member_books, txn_id, return_dt
            )
            if ok:
                save_all(books, members, transactions, member_books)
                st.success(msg)
                if delay_info.get("is_delayed"):
                    st.warning(
                        f"Fine breakdown: {delay_info['days_overdue']} day(s) "
                        f"× ₹{delay_info['fine_per_day']:.2f}/day "
                        f"= **₹{delay_info['total_fine']:.2f}**"
                    )
            else:
                st.error(msg)


# ─────────────────────────────────────────────────────────────
# TAB 5 – REPORTS
# ─────────────────────────────────────────────────────────────
with tab_reports:
    st.header("Reports & Analytics")

    # ── Summary metrics ────────────────────────────────────
    open_borrows = get_open_borrows(transactions)
    overdue_list = get_overdue_borrows(transactions)
    fines_total  = total_fines_collected(transactions)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Book Titles",      len(books))
    m2.metric("Total Copies",     sum(b["total_copies"]    for b in books))
    m3.metric("Available Copies", sum(b["available_copies"] for b in books))
    m4.metric("Active Members",   sum(1 for m in members if m["status"] == "active"))
    m5.metric("Active Loans",     len(open_borrows))
    m6.metric("Total Fines ₹",    f"{fines_total:.2f}")

    st.divider()

    # ── Overdue books ──────────────────────────────────────
    st.subheader("⚠️ Overdue Books")
    if overdue_list:
        rows = []
        for t in overdue_list:
            b       = find_book(books, t["book_id"])
            m       = find_member(members, t["member_id"])
            due     = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
            overdue = (date.today() - due).days
            rows.append({
                "Txn ID":         t["transaction_id"],
                "Book":           b["title"]  if b else t["book_id"],
                "Member":         m["name"]   if m else t["member_id"],
                "Member E-mail":  m["email"]  if m else "—",
                "Due Date":       t["due_date"],
                "Days Overdue":   overdue,
                "Accrued Fine ₹": round(overdue * FINE_PER_DAY, 2),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.success("No overdue books — great! 🎉")

    st.divider()

    # ── Full transaction history ───────────────────────────
    st.subheader("📋 Full Transaction History")
    if transactions:
        rows = []
        for t in transactions:
            b    = find_book(books, t["book_id"])
            m    = find_member(members, t["member_id"])
            fine = t.get("delay_info", {}).get("total_fine", "—")
            rows.append({
                "Txn ID":      t["transaction_id"],
                "Type":        "Return" if "borrow_transaction_id" in t else "Borrow",
                "Book":        b["title"] if b else t["book_id"],
                "Member":      m["name"]  if m else t["member_id"],
                "Borrow Date": t["borrow_date"],
                "Due Date":    t["due_date"],
                "Return Date": t.get("return_date") or "—",
                "Status":      t["status"].capitalize(),
                "Fine ₹":      f"{fine:.2f}" if isinstance(fine, float) else "—",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions recorded yet.")

    st.divider()

    # ── Member borrow history lookup ───────────────────────
    st.subheader("🔍 Member Borrow History")
    if members:
        member_lookup = {
            f"{m['name']} ({m['member_id']})": m["member_id"] for m in members
        }
        sel = st.selectbox("Select a Member", list(member_lookup.keys()), key="rep_member")
        mid = member_lookup[sel]
        hist = get_member_history(transactions, mid)
        if hist:
            rows = []
            for t in hist:
                b    = find_book(books, t["book_id"])
                fine = "—"
                # Find the matching return transaction
                for rt in transactions:
                    if rt.get("borrow_transaction_id") == t["transaction_id"]:
                        di   = rt.get("delay_info", {})
                        fine = f"₹{di.get('total_fine', 0):.2f}"
                        break
                rows.append({
                    "Txn ID":      t["transaction_id"],
                    "Book":        b["title"] if b else t["book_id"],
                    "Borrow Date": t["borrow_date"],
                    "Due Date":    t["due_date"],
                    "Return Date": t.get("return_date") or "Not returned",
                    "Status":      t["status"].capitalize(),
                    "Fine":        fine,
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No borrow history for this member.")
    else:
        st.info("No members registered yet.")

    st.divider()

    # ── Book inventory summary ─────────────────────────────
    st.subheader("📦 Book Inventory Summary")
    if books:
        st.dataframe(
            [
                {
                    "ID":        b["book_id"],
                    "Title":     b["title"],
                    "Author":    b["author"],
                    "Genre":     b["genre"],
                    "Total":     b["total_copies"],
                    "Available": b["available_copies"],
                    "Borrowed":  b["total_copies"] - b["available_copies"],
                    "Status":    b["status"].capitalize(),
                }
                for b in books
            ],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No books in the system.")
