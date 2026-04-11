"""
Library Management System - Streamlit UI
=========================================
Streamlit interface for the Library Management System
"""

import streamlit as st
from streamlit_searchbox import st_searchbox
from datetime import date, datetime
import pandas as pd
from appHelper import (
    load_all,
    save_all,
    find_book,
    find_member,
    add_book,
    register_member,
    borrow_book,
    return_book,
    get_open_borrow_transactions,
    get_open_member_borrows,
    get_open_overdue_borrow_transactions,
    total_fines_collected,
    FINE_PER_DAY,
    MAX_BORROW_DAYS,
)


# ═════════════════════════════════════════════════════════════
# SECTION 6 ── STREAMLIT UI
# ═════════════════════════════════════════════════════════════

st.set_page_config(page_title="Library Management System", page_icon="📚", layout="wide")
st.title("📚 Library Management System")

# Load once per script run
books, members, transactions, member_books = load_all()

tab_add_book, tab_add_member,  tab_quick_borrow, tab_return, tab_member_info, tab_reports = st.tabs([
    "➕ Add Book",
    "👤 Register Member",
    "🔎 Quick Borrow",
    "📥 Return Book",
    "🧾 Member Info",
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
                save_all(books, members, transactions, member_books)
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
                save_all(books, members, transactions, member_books)
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
# TAB 4 – QUICK BORROW (SEARCH MEMBER + BOOK)
# ─────────────────────────────────────────────────────────────
with tab_quick_borrow:
    st.header("Quick Borrow")

    member_id_query = st.text_input(
        "Search by Member ID",
        placeholder="e.g. M0001",
        key="qb_member_id"
    ).strip().upper()

    book_name_query = st.text_input(
        "Search Book by Name",
        placeholder="Type full or partial title",
        key="qb_book_name"
    ).strip()

    if not member_id_query and not book_name_query:
        st.info("Enter Member ID and Book Name to search.")
    else:
        member = find_member(members, member_id_query) if member_id_query else None

        if member_id_query and not member:
            st.error(f"Member {member_id_query} not found.")
        elif member and member.get("status") != "active":
            st.error(f"Member {member_id_query} is not active.")
        else:
            # Match only available books by title
            matched_books = [
                b for b in books
                if b.get("available_copies", 0) > 0
                and book_name_query.lower() in b.get("title", "").lower()
            ] if book_name_query else []

            if book_name_query and not matched_books:
                st.warning("No available books match that title.")
            elif member and matched_books:
                st.success(f"Member found: {member['name']} ({member['member_id']})")

                borrow_dt = st.date_input("Borrow Date", value=date.today(), key="qb_borrow_date")

                # Table header
                h1, h2, h3, h4, h5 = st.columns([3, 2, 1, 1, 1])
                h1.markdown("**Title**")
                h2.markdown("**Author**")
                h3.markdown("**Book ID**")
                h4.markdown("**Available**")
                h5.markdown("**Action**")

                for b in matched_books:
                    c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 1])
                    c1.write(b.get("title", "—"))
                    c2.write(b.get("author", "—"))
                    c3.write(b.get("book_id", "—"))
                    c4.write(b.get("available_copies", 0))

                    if c5.button("Borrow", key=f"qb_borrow_{member['member_id']}_{b['book_id']}"):
                        ok, msg, books, members, transactions, member_books = borrow_book(
                            books,
                            members,
                            transactions,
                            member_books,
                            b["book_id"],
                            member["member_id"],
                            borrow_dt,
                        )
                        if ok:
                            save_all(books, members, transactions, member_books)
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

# ─────────────────────────────────────────────────────────────
# TAB 4 – RETURN BOOK
# ─────────────────────────────────────────────────────────────
with tab_return:
    st.header("Return a Book")

    member_id_query = st.text_input("Enter Member ID", placeholder="e.g. M0001").strip().upper()

    if not member_id_query:
        st.info("Enter a Member ID to view transactions.")
    else:
        member = find_member(members, member_id_query)
        if not member:
            st.error(f"Member {member_id_query} not found.")
        else:
            st.subheader(f"Member: {member['name']} ({member['member_id']})")

            # All transactions for this member (borrow + return)
            member_txns = [t for t in transactions if t["member_id"] == member_id_query]


            st.markdown("### Transactions")
            if member_txns:
                rows = []
                for t in member_txns:
                    b = find_book(books, t["book_id"])
                    rows.append({
                        "Txn ID": t["transaction_id"],
                        "Type": "Return" if "borrow_transaction_id" in t else "Borrow",
                        "Book": b["title"] if b else t["book_id"],
                        "Borrow Date": t.get("borrow_date"),
                        "Due Date": t.get("due_date"),
                        "Return Date": t.get("return_date") or "—",
                        "Status": t.get("status", "").capitalize(),
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.info("No transactions found for this member.")

            st.markdown("### Borrowed (Not Yet Returned)")
            closed_borrow_ids = {
                t["borrow_transaction_id"]
                for t in transactions
                if "borrow_transaction_id" in t
            }
            open_member_borrows = [
                t for t in get_open_borrows(transactions)
                if (
                    t["member_id"] == member_id_query
                    and t["transaction_id"] not in closed_borrow_ids
                )
            ]
            open_borrows = get_open_member_borrows(transactions, member_id_query)

            if not open_borrows:
                st.success("No active borrowed books for this member.")
            else:
                # Optional single return date for all return actions
                return_dt = st.date_input("Return Date", value=date.today(), key="return_date_for_member")

                for t in open_borrows:
                    b = find_book(books, t["book_id"])
                    book_title = b["title"] if b else t["book_id"]

                    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
                    c1.write(f"**Txn:** {t['transaction_id']}")
                    c2.write(f"**Book:** {book_title}")
                    c3.write(f"**Borrowed:** {t['borrow_date']}")
                    c4.write(f"**Due:** {t['due_date']}")

                    if c5.button("Return", key=f"btn_return_{t['transaction_id']}"):
                        ok, msg, delay_info, books, transactions, member_books = return_book(
                            books, transactions, member_books, t["transaction_id"], return_dt
                        )
                        if ok:
                            save_all(books, members, transactions, member_books)
                            st.success(msg)
                            if delay_info.get("is_delayed"):
                                st.warning(
                                    f"Fine: {delay_info['days_overdue']} day(s) × "
                                    f"₹{delay_info['fine_per_day']:.2f} = ₹{delay_info['total_fine']:.2f}"
                                )
                            st.rerun()
                        else:
                            st.error(msg)

# ─────────────────────────────────────────────────────────────
# TAB 6 – MEMBER INFO
# ─────────────────────────────────────────────────────────────
with tab_member_info:
    st.header("Member Info")

    member_id_info = st.text_input(
        "Enter Member ID",
        placeholder="e.g. M0001",
        key="member_info_id"
    ).strip().upper()

    if not member_id_info:
        st.info("Enter a Member ID to view member information.")
    else:
        member = find_member(members, member_id_info)
        if not member:
            st.error(f"Member {member_id_info} not found.")
        else:
            st.subheader(f"{member['name']} ({member['member_id']})")

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Status", str(member.get("status", "-")).capitalize())
            mc2.metric("E-mail", member.get("email", "-"))
            mc3.metric("Phone", member.get("phone", "-"))
            mc4.metric("Member Since", member.get("membership_date", "-"))

            addr = member.get("address", {})
            st.caption(
                f"Address: {addr.get('street', '')}, {addr.get('city', '')}, {addr.get('postal_code', '')}".strip(", ")
            )

            st.markdown("### Unreturned Books")
            open_member_borrows = get_open_member_borrows(transactions, member_id_info)

            if open_member_borrows:
                rows = []
                today = date.today()
                total_overdue_fine = 0.0

                for t in open_member_borrows:
                    b = find_book(books, t["book_id"])
                    due = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
                    overdue_days = max(0, (today - due).days)
                    fine = round(overdue_days * FINE_PER_DAY, 2)
                    total_overdue_fine += fine

                    rows.append({
                        "Txn ID": t["transaction_id"],
                        "Book": b["title"] if b else t["book_id"],
                        "Borrow Date": t.get("borrow_date", "-"),
                        "Due Date": t.get("due_date", "-"),
                        "Days Overdue": overdue_days if overdue_days > 0 else 0,
                        "Accrued Fine ₹": fine,
                    })

                st.metric("Current Fine on Unreturned Books (₹)", f"{total_overdue_fine:.2f}")

                open_df = pd.DataFrame(rows)

                def highlight_overdue(row):
                    due = datetime.strptime(str(row["Due Date"]), "%Y-%m-%d").date()
                    return ["background-color: #ffe6e6" if due < date.today() else "" for _ in row]

                st.dataframe(
                    open_df.style.apply(highlight_overdue, axis=1),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.success("No unreturned books for this member.")

            st.markdown("### All Transactions")
            member_txns = [t for t in transactions if t.get("member_id") == member_id_info]

            if member_txns:
                tx_rows = []
                for t in member_txns:
                    b = find_book(books, t["book_id"])
                    fine = t.get("delay_info", {}).get("total_fine", 0.0)
                    tx_rows.append({
                        "Txn ID": t.get("transaction_id"),
                        "Type": "Return" if t.get("borrow_transaction_id") else "Borrow",
                        "Book": b["title"] if b else t.get("book_id"),
                        "Borrow Date": t.get("borrow_date") or "-",
                        "Due Date": t.get("due_date") or "-",
                        "Return Date": t.get("return_date") or "-",
                        "Status": str(t.get("status", "")).capitalize(),
                        "Fine ₹": f"{fine:.2f}",
                    })
                st.dataframe(tx_rows, use_container_width=True, hide_index=True)
            else:
                st.info("No transactions found for this member.")

# ─────────────────────────────────────────────────────────────
# TAB 7 – REPORTS
# ─────────────────────────────────────────────────────────────
with tab_reports:
    st.header("Reports & Analytics")

    # ── Summary metrics ────────────────────────────────────
    open_borrows = get_open_borrow_transactions(transactions)
    overdue_list = get_open_overdue_borrow_transactions(transactions)
    fines_total  = total_fines_collected(open_borrows)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Book Titles",      len(books))
    m2.metric("Total Copies",     sum(b["total_copies"]    for b in books))
    m3.metric("Available Copies", sum(b["available_copies"] for b in books))
    m4.metric("Active Members",   sum(1 for m in members if m["status"] == "active"))
    m5.metric("Active Loans",     len(open_borrows))
    m6.metric("Total Fines ₹",    f"{fines_total:.2f}")

    st.divider()

    # ── All Unreturned Books ───────────────────────────────────────
    st.subheader("📖 All Unreturned Books")
    all_unreturned = get_open_borrow_transactions(transactions)

    if all_unreturned:
        rows = []
        today = date.today()

        for t in all_unreturned:
            b       = find_book(books, t["book_id"])
            m       = find_member(members, t["member_id"])
            due     = datetime.strptime(t["due_date"], "%Y-%m-%d").date()
            overdue = (today - due).days
            is_overdue = overdue > 0
            fine = round(overdue * FINE_PER_DAY, 2) if is_overdue else 0.0

            rows.append({
                "Txn ID":         t["transaction_id"],
                "Book":           b["title"]  if b else t["book_id"],
                "Member":         m["name"]   if m else t["member_id"],
                "Member E-mail":  m["email"]  if m else "—",
                "Borrow Date":    t["borrow_date"],
                "Due Date":       t["due_date"],
                "Days Overdue":   max(0, overdue),
                "Accrued Fine ₹": f"{fine:.2f}",
                "Status":         "Overdue" if is_overdue else "On Time",
            })

        unreturned_df = pd.DataFrame(rows)

        def highlight_overdue_rows(row):
            if row["Days Overdue"] > 0:
                return ["background-color: #ffe6e6"] * len(row)
            return ["background-color: #ffffff"] * len(row)

        st.dataframe(
            unreturned_df.style.apply(highlight_overdue_rows, axis=1),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("All books have been returned! 📚")

    st.divider()


    # ── Member borrow history lookup ───────────────────────
    st.subheader("🔍 Member Active Borrow Books")
    if members:
        member_lookup = {
            f"{m['name']} ({m['member_id']})": m["member_id"] for m in members
        }


        def search_member(searchterm: str) -> list:
            """Return matching member options based on search term"""
            if not searchterm:
                return list(member_lookup.keys())
            return [
                member_name for member_name in member_lookup.keys()
                if searchterm.lower() in member_name.lower()
            ]


        sel = st_searchbox(
            search_function=search_member,
            placeholder="Search member by name or ID...",
            label="Select a Member",
            default=list(member_lookup.keys())[0] if member_lookup else None,
        )

        if sel:
            mid = member_lookup[sel]
        hist = get_open_member_borrows(transactions, mid)
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
