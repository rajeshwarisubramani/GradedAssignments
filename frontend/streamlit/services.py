import json
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

BOOKS_FILE = DATA_DIR / "Books.json"
MEMBERS_FILE = DATA_DIR / "Member.json"
LOANS_FILE = DATA_DIR / "Transactions.json"


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


def _load(path, default):
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


def _save(path, data):
    payload = data
    if path == BOOKS_FILE:
        payload = _to_storage_books(data)
    elif path == MEMBERS_FILE:
        payload = _to_storage_members(data)
    elif path == LOANS_FILE:
        payload = _to_storage_transactions(data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_data():
    books = _load(BOOKS_FILE, {})
    members = _load(MEMBERS_FILE, {})
    loans = _load(LOANS_FILE, [])
    return books, members, loans


def save_books(books):
    _save(BOOKS_FILE, books)


def save_members(members):
    _save(MEMBERS_FILE, members)


def save_loans(loans):
    _save(LOANS_FILE, loans)


def next_id(collection, prefix):
    nums = []
    for key in collection.keys():
        if isinstance(key, str) and key.startswith(prefix) and key[1:].isdigit():
            nums.append(int(key[1:]))
    return f"{prefix}{(max(nums) + 1) if nums else 1:04d}"


def next_loan_id(loans):
    nums = []
    for loan in loans:
        lid = str(loan.get("loan_id", ""))
        if len(lid) > 1 and lid[1:].isdigit():
            nums.append(int(lid[1:]))
    return f"T{(max(nums) + 1) if nums else 1:03d}"


def add_book(books, title, author, copies):
    title = title.strip()
    author = author.strip()
    if not title or not author:
        raise ValueError("Title and Author are required.")

    duplicate = any(
        b["title"].lower() == title.lower() and b["author"].lower() == author.lower()
        for b in books.values()
    )
    if duplicate:
        raise ValueError("A book with the same title and author already exists.")

    bid = next_id(books, "B")
    books[bid] = {
        "id": bid,
        "title": title,
        "author": author,
        "copies_total": int(copies),
        "copies_available": int(copies),
    }
    save_books(books)
    return bid


def register_member(members, name, email):
    name = name.strip()
    email = email.strip()

    if not name or not email:
        raise ValueError("Name and Email are required.")

    if any(m["email"].lower() == email.lower() for m in members.values()):
        raise ValueError("A member with this email already exists.")

    mid = next_id(members, "M")
    members[mid] = {"id": mid, "name": name, "email": email}
    save_members(members)
    return mid


def get_available_books(books):
    return {bid: b for bid, b in books.items() if b["copies_available"] > 0}


def get_active_loans(loans):
    return [l for l in loans if l["return_date"] is None]


def borrow_book(books, members, loans, book_id, member_id, borrow_date):
    already = any(
        l["book_id"] == book_id and l["member_id"] == member_id and l["return_date"] is None
        for l in loans
    )
    if already:
        raise ValueError("This member already has this book borrowed.")

    loan_id = next_loan_id(loans)
    loans.append(
        {
            "loan_id": loan_id,
            "book_id": book_id,
            "member_id": member_id,
            "borrow_date": str(borrow_date),
            "return_date": None,
        }
    )
    books[book_id]["copies_available"] -= 1

    save_loans(loans)
    save_books(books)
    return loan_id


def build_return_options(active_loans, books, members):
    loan_labels = {}
    for l in active_loans:
        book = books.get(l["book_id"], {})
        member = members.get(l["member_id"], {})
        label = (
            f"Loan {l['loan_id']} | "
            f"{book.get('title', '?')} -> {member.get('name', '?')} "
            f"(borrowed {l['borrow_date']})"
        )
        loan_labels[label] = l["loan_id"]
    return loan_labels


def return_book(books, loans, loan_id, return_date):
    target = None
    for loan in loans:
        if loan["loan_id"] == loan_id:
            target = loan
            break

    if target is None:
        raise ValueError("Loan not found.")
    if target["return_date"] is not None:
        raise ValueError("This loan is already returned.")

    target["return_date"] = str(return_date)
    books[target["book_id"]]["copies_available"] += 1

    save_loans(loans)
    save_books(books)


def metrics(books, members, loans):
    return len(books), len(members), sum(1 for l in loans if l["return_date"] is None)


def books_table_rows(books):
    return [
        {
            "ID": b["id"],
            "Title": b["title"],
            "Author": b["author"],
            "Total": b["copies_total"],
            "Available": b["copies_available"],
        }
        for b in books.values()
    ]


def members_table_rows(members):
    return [{"ID": m["id"], "Name": m["name"], "Email": m["email"]} for m in members.values()]


def active_report_rows(active_loans, books, members):
    rows = []
    for l in active_loans:
        book = books.get(l["book_id"], {})
        member = members.get(l["member_id"], {})
        rows.append(
            {
                "Loan ID": l["loan_id"],
                "Book": book.get("title", "?"),
                "Author": book.get("author", "?"),
                "Member": member.get("name", "?"),
                "Borrow Date": l["borrow_date"],
            }
        )
    return rows


def history_report_rows(loans, books, members):
    rows = []
    for l in loans:
        book = books.get(l["book_id"], {})
        member = members.get(l["member_id"], {})
        rows.append(
            {
                "Loan ID": l["loan_id"],
                "Book": book.get("title", "?"),
                "Member": member.get("name", "?"),
                "Borrow Date": l["borrow_date"],
                "Return Date": l["return_date"] or "-",
                "Status": "Returned" if l["return_date"] else "Active",
            }
        )
    return rows


def inventory_rows(books):
    return [
        {
            "ID": b["id"],
            "Title": b["title"],
            "Author": b["author"],
            "Total": b["copies_total"],
            "Available": b["copies_available"],
            "Borrowed": b["copies_total"] - b["copies_available"],
        }
        for b in books.values()
    ]

