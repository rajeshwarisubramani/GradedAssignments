import streamlit as st
import json
from datetime import date, datetime, timedelta

# ── File paths ──────────────────────────────────────────────────────────────
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

BOOKS_FILE   = DATA_DIR / "Books.json"
MEMBERS_FILE = DATA_DIR / "Member.json"
LOANS_FILE   = DATA_DIR / "Transactions.json"

# ── Persistence helpers ──────────────────────────────────────────────────────
def _to_internal_books(raw):
    if isinstance(raw, dict):
        return raw
    books_dict = {}
    for b in raw or []:
        bid = b.get("book_id") or b.get("id")
        if not bid:
            continue
        total = int(b.get("total_copies", b.get("copies_total", 1)))
        available = int(b.get("available_copies", b.get("copies_available", total)))
        books_dict[bid] = {
            "id": bid,
            "title": b.get("title", ""),
            "author": b.get("author", ""),
            "copies_total": total,
            "copies_available": available,
            "genre": b.get("genre", "General"),
            "isbn": b.get("isbn", ""),
            "publication_year": b.get("publication_year"),
            "status": b.get("status", "available"),
        }
    return books_dict


def _to_internal_members(raw):
    if isinstance(raw, dict):
        return raw
    members_dict = {}
    for m in raw or []:
        mid = m.get("member_id") or m.get("id")
        if not mid:
            continue
        members_dict[mid] = {
            "id": mid,
            "name": m.get("name", ""),
            "email": m.get("email", ""),
            "phone": m.get("phone", ""),
            "membership_date": m.get("membership_date"),
            "status": m.get("status", "active"),
            "address": m.get("address", {}),
        }
    return members_dict


def _to_internal_loans(raw):
    # Legacy app format already
    if raw and isinstance(raw, list) and "loan_id" in raw[0]:
        return raw

    loans_map = {}
    for t in raw or []:
        tid = t.get("transaction_id")
        if not tid:
            continue

        if t.get("event") == "return" and t.get("ref_transaction_id"):
            ref = t["ref_transaction_id"]
            if ref in loans_map:
                loans_map[ref]["return_date"] = t.get("return_date")
            continue

        if t.get("status") == "borrowed" or t.get("event") == "borrow":
            loans_map[tid] = {
                "loan_id": tid,
                "book_id": t.get("book_id"),
                "member_id": t.get("member_id"),
                "borrow_date": t.get("borrow_date"),
                "return_date": t.get("return_date"),
            }

    # Handle non-event rows where status may be returned in same row
    for t in raw or []:
        tid = t.get("transaction_id")
        if tid in loans_map and t.get("status") == "returned" and t.get("return_date"):
            loans_map[tid]["return_date"] = t.get("return_date")

    return list(loans_map.values())


def _to_storage_books(data):
    if isinstance(data, list):
        return data
    return [
        {
            "book_id": bid,
            "title": b.get("title", ""),
            "author": b.get("author", ""),
            "isbn": b.get("isbn", ""),
            "genre": b.get("genre", "General"),
            "publication_year": b.get("publication_year"),
            "total_copies": int(b.get("copies_total", 0)),
            "available_copies": int(b.get("copies_available", 0)),
            "status": "available" if int(b.get("copies_available", 0)) > 0 else "unavailable",
        }
        for bid, b in data.items()
    ]


def _to_storage_members(data):
    if isinstance(data, list):
        return data
    return [
        {
            "member_id": mid,
            "name": m.get("name", ""),
            "email": m.get("email", ""),
            "phone": m.get("phone", ""),
            "membership_date": m.get("membership_date") or str(date.today()),
            "status": m.get("status", "active"),
            "address": m.get("address", {}),
        }
        for mid, m in data.items()
    ]


def _to_storage_transactions(data):
    if not data:
        return []
    if isinstance(data, list) and "transaction_id" in data[0]:
        return data

    out = []
    for loan in data:
        borrow_date = str(loan.get("borrow_date"))
        try:
            due_date = (datetime.strptime(borrow_date, "%Y-%m-%d").date() + timedelta(days=15)).isoformat()
        except Exception:
            due_date = borrow_date

        return_date = loan.get("return_date")
        status = "returned" if return_date else "borrowed"
        out.append(
            {
                "transaction_id": loan.get("loan_id"),
                "member_id": loan.get("member_id"),
                "book_id": loan.get("book_id"),
                "borrow_date": borrow_date,
                "due_date": due_date,
                "return_date": return_date,
                "status": status,
                "max_borrow_days": 15,
                "delay_info": {
                    "is_delayed": False,
                    "days_overdue": 0,
                    "return_date_actual": return_date,
                    "fine_per_day": 5.0,
                    "total_fine": 0.0,
                },
            }
        )
    return out


def load(path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if path == BOOKS_FILE:
            return _to_internal_books(raw)
        if path == MEMBERS_FILE:
            return _to_internal_members(raw)
        if path == LOANS_FILE:
            return _to_internal_loans(raw)
        return raw
    return default


def save(path, data):
    payload = data
    if path == BOOKS_FILE:
        payload = _to_storage_books(data)
    elif path == MEMBERS_FILE:
        payload = _to_storage_members(data)
    elif path == LOANS_FILE:
        payload = _to_storage_transactions(data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
# ── Data (dicts keyed by ID) ─────────────────────────────────────────────────
# books   = { book_id:   {"id", "title", "author", "copies_total", "copies_available"} }
# members = { member_id: {"id", "name",  "email"} }
# loans   = [ {"loan_id", "book_id", "member_id", "borrow_date", "return_date"} ]

books   = load(BOOKS_FILE,   {})
members = load(MEMBERS_FILE, {})
loans   = load(LOANS_FILE,   [])

def next_id(collection: dict, prefix: str) -> str:
    nums = []
    for key in collection.keys():
        if isinstance(key, str) and key.startswith(prefix) and key[1:].isdigit():
            nums.append(int(key[1:]))
    return f"{prefix}{(max(nums) + 1) if nums else 1:04d}"

def next_loan_id() -> str:
    nums = []
    for loan in loans:
        lid = str(loan.get("loan_id", ""))
        if len(lid) > 1 and lid[1:].isdigit():
            nums.append(int(lid[1:]))
    return f"T{(max(nums) + 1) if nums else 1:03d}"

# ── Streamlit UI ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Library Manager", page_icon="📚", layout="wide")
st.title("📚 Library Management System")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Add Book", "Register Member", "Borrow Book", "Return Book", "Reports"]
)

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 – Add Book
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("Add a New Book")
    with st.form("add_book_form"):
        title  = st.text_input("Title")
        author = st.text_input("Author")
        copies = st.number_input("Number of Copies", min_value=1, value=1, step=1)
        submitted = st.form_submit_button("Add Book")

    if submitted:
        if not title.strip() or not author.strip():
            st.error("Title and Author are required.")
        else:
            # Check for duplicate title+author
            duplicate = any(
                b["title"].lower() == title.strip().lower() and
                b["author"].lower() == author.strip().lower()
                for b in books.values()
            )
            if duplicate:
                st.warning("A book with the same title and author already exists.")
            else:
                bid = next_id(books, "B")
                books[bid] = {
                    "id": bid,
                    "title": title.strip(),
                    "author": author.strip(),
                    "copies_total": int(copies),
                    "copies_available": int(copies),
                }
                save(BOOKS_FILE, books)
                st.success(f"Book added! ID: **{bid}**")

    if books:
        st.subheader("All Books")
        st.table([
            {
                "ID": b["id"], "Title": b["title"], "Author": b["author"],
                "Total": b["copies_total"], "Available": b["copies_available"]
            }
            for b in books.values()
        ])

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 – Register Member
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("Register a New Member")
    with st.form("add_member_form"):
        name  = st.text_input("Full Name")
        email = st.text_input("Email")
        submitted2 = st.form_submit_button("Register")

    if submitted2:
        if not name.strip() or not email.strip():
            st.error("Name and Email are required.")
        elif any(m["email"].lower() == email.strip().lower() for m in members.values()):
            st.warning("A member with this email already exists.")
        else:
            mid = next_id(members, "M")
            members[mid] = {"id": mid, "name": name.strip(), "email": email.strip()}
            save(MEMBERS_FILE, members)
            st.success(f"Member registered! ID: **{mid}**")

    if members:
        st.subheader("All Members")
        st.table([{"ID": m["id"], "Name": m["name"], "Email": m["email"]}
                  for m in members.values()])

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 – Borrow Book
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("Borrow a Book")

    if not books:
        st.info("No books in the system yet.")
    elif not members:
        st.info("No members registered yet.")
    else:
        # Only show books that have available copies
        available_books = {bid: b for bid, b in books.items() if b["copies_available"] > 0}

        if not available_books:
            st.warning("All books are currently borrowed.")
        else:
            with st.form("borrow_form"):
                book_options   = {f"{b['title']} by {b['author']} (ID: {bid})": bid
                                  for bid, b in available_books.items()}
                member_options = {f"{m['name']} (ID: {mid})": mid
                                  for mid, m in members.items()}

                selected_book   = st.selectbox("Select Book",   list(book_options.keys()))
                selected_member = st.selectbox("Select Member", list(member_options.keys()))
                borrow_date     = st.date_input("Borrow Date", value=date.today())
                submitted3      = st.form_submit_button("Borrow")

            if submitted3:
                bid = book_options[selected_book]
                mid = member_options[selected_member]

                # Check if this member already has this book borrowed
                already = any(
                    l["book_id"] == bid and l["member_id"] == mid and l["return_date"] is None
                    for l in loans
                )
                if already:
                    st.error("This member already has this book borrowed.")
                else:
                    loans.append({
                        "loan_id":     next_loan_id(),
                        "book_id":     bid,
                        "member_id":   mid,
                        "borrow_date": str(borrow_date),
                        "return_date": None,
                    })
                    books[bid]["copies_available"] -= 1
                    save(LOANS_FILE, loans)
                    save(BOOKS_FILE, books)
                    st.success(f"Book borrowed successfully! Loan ID: **{loans[-1]['loan_id']}**")

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 – Return Book
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("Return a Book")

    active_loans = [l for l in loans if l["return_date"] is None]

    if not active_loans:
        st.info("No books are currently borrowed.")
    else:
        # Build display labels for each active loan
        loan_labels = {}
        for l in active_loans:
            book   = books.get(l["book_id"],   {})
            member = members.get(l["member_id"], {})
            label  = (
                f"Loan {l['loan_id']} | "
                f"{book.get('title','?')} → {member.get('name','?')} "
                f"(borrowed {l['borrow_date']})"
            )
            loan_labels[label] = l["loan_id"]

        with st.form("return_form"):
            selected_loan = st.selectbox("Select Loan to Return", list(loan_labels.keys()))
            return_date   = st.date_input("Return Date", value=date.today())
            submitted4    = st.form_submit_button("Return")

        if submitted4:
            loan_id = loan_labels[selected_loan]
            for l in loans:
                if l["loan_id"] == loan_id:
                    l["return_date"] = str(return_date)
                    books[l["book_id"]]["copies_available"] += 1
                    break
            save(LOANS_FILE, loans)
            save(BOOKS_FILE, books)
            st.success("Book returned successfully!")

# ════════════════════════════════════════════════════════════════════════════
# TAB 5 – Reports
# ════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("Reports")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Books (titles)",  len(books))
    col2.metric("Total Members",         len(members))
    col3.metric("Active Loans",          sum(1 for l in loans if l["return_date"] is None))

    st.divider()

    # ── Currently Borrowed ──────────────────────────────────────────────────
    st.subheader("📖 Currently Borrowed Books")
    active = [l for l in loans if l["return_date"] is None]
    if active:
        rows = []
        for l in active:
            book   = books.get(l["book_id"],   {})
            member = members.get(l["member_id"], {})
            rows.append({
                "Loan ID":     l["loan_id"],
                "Book":        book.get("title", "?"),
                "Author":      book.get("author", "?"),
                "Member":      member.get("name", "?"),
                "Borrow Date": l["borrow_date"],
            })
        st.table(rows)
    else:
        st.info("No books currently borrowed.")

    st.divider()

    # ── Full Loan History ───────────────────────────────────────────────────
    st.subheader("📋 Full Loan History")
    if loans:
        rows = []
        for l in loans:
            book   = books.get(l["book_id"],   {})
            member = members.get(l["member_id"], {})
            rows.append({
                "Loan ID":      l["loan_id"],
                "Book":         book.get("title", "?"),
                "Member":       member.get("name", "?"),
                "Borrow Date":  l["borrow_date"],
                "Return Date":  l["return_date"] or "—",
                "Status":       "Returned" if l["return_date"] else "Active",
            })
        st.table(rows)
    else:
        st.info("No loan history yet.")

    st.divider()

    # ── Book Inventory Summary ──────────────────────────────────────────────
    st.subheader("📦 Book Inventory")
    if books:
        st.table([
            {
                "ID":        b["id"],
                "Title":     b["title"],
                "Author":    b["author"],
                "Total":     b["copies_total"],
                "Available": b["copies_available"],
                "Borrowed":  b["copies_total"] - b["copies_available"],
            }
            for b in books.values()
        ])
    else:
        st.info("No books in the system.")