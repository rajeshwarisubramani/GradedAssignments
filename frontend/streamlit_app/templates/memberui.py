from __future__ import annotations

from typing import Any
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from ..service import BaseService


def _ensure_member_state() -> None:
    st.session_state.setdefault("selected_member_id", None)
    st.session_state.setdefault("selected_member", None)
    st.session_state.setdefault("pending_return", None)


@st.dialog("Confirm Return")
def _return_confirmation_dialog(service: "BaseService") -> None:
    pending = st.session_state.get("pending_return")
    if not pending:
        return

    book_id = pending.get("book_id", "")
    member_id = pending.get("member_id", "")
    title = pending.get("title", "")
    st.write(f"Are you sure you want to return **{book_id}** ({title or 'Untitled'})?")

    confirm_col, cancel_col = st.columns(2)
    if confirm_col.button("Confirm Return", type="primary"):
        try:
            tx = service.return_book(member_id, book_id)
            print(tx)
            st.session_state["last_return_tx"] = tx
            st.session_state["last_return_msg"] = f"Returned {book_id} successfully."
            st.session_state["pending_return"] = None
            st.rerun()
        except Exception as exc:
            st.error(f"Return failed: {exc}")

    if cancel_col.button("Cancel"):
        st.session_state["pending_return"] = None
        st.rerun()


def _filter_members(
    members: list[dict[str, Any]], member_id_query: str, name_query: str
) -> list[dict[str, Any]]:
    member_id_query = member_id_query.strip().lower()
    name_query = name_query.strip().lower()

    filtered: list[dict[str, Any]] = []
    for member in members:
        member_id = str(member.get("member_id", "")).lower()
        name = str(member.get("name", "")).lower()
        matches_id = not member_id_query or member_id_query in member_id
        matches_name = not name_query or name_query in name
        if matches_id and matches_name:
            filtered.append(member)
    return filtered


def _render_members_table(members: list[dict[str, Any]]) -> None:
    if not members:
        st.info("No members found.")
        return

    header = st.columns([2, 3, 1, 3, 1])
    header[0].markdown("**Member ID**")
    header[1].markdown("**Name**")
    header[2].markdown("**Age**")
    header[3].markdown("**Contact**")
    header[4].markdown("**Action**")

    for idx, member in enumerate(members):
        member_id = str(member.get("member_id", ""))
        row = st.columns([2, 3, 1, 3, 1])
        row[0].write(member_id)
        row[1].write(member.get("name", "-"))
        row[2].write(member.get("age", "-"))
        row[3].write(member.get("contact_info", "-"))
        if row[4].button("Open", key=f"open_member_{member_id}_{idx}", type="primary"):
            st.session_state["selected_member_id"] = member_id
            st.session_state["selected_member"] = member
            st.rerun()


def _render_member_list_view(service: BaseService) -> None:
    st.subheader("Member Info")
    col1, col2 = st.columns(2)
    member_id_query = col1.text_input("Search by Member ID")
    name_query = col2.text_input("Search by Name")

    try:
        members = service.list_members().get("items", [])
    except Exception as exc:
        st.error(f"Unable to load members: {exc}")
        return

    filtered = _filter_members(members, member_id_query, name_query)
    st.caption(f"Showing {len(filtered)} of {len(members)} members")
    _render_members_table(filtered)


def _render_member_info_panel(member: dict[str, Any]) -> None:
    st.subheader("Member Details")
    st.write(f"**Member ID:** {member.get('member_id', '-')}")
    st.write(f"**Name:** {member.get('name', '-')}")
    st.write(f"**Age:** {member.get('age', '-')}")
    st.write(f"**Contact:** {member.get('contact_info', '-')}")


def _render_member_history_panel(service: BaseService, member_id: str) -> None:
    st.subheader("Previous Transactions")
    try:
        result = service.report_member_history(member_id)
        items = result.get("items", [])
    except Exception as exc:
        st.error(f"Unable to load member history: {exc}")
        return

    if not items:
        st.info("No previous transactions found for this member.")
        return
    st.dataframe(items, use_container_width=True)


def _render_borrow_books_panel(service: BaseService, member_id: str) -> None:
    st.subheader("Borrow Books")
    with st.form("borrow_form"):
        borrow_book_id = st.text_input("Book ID to Borrow")
        borrow_submit = st.form_submit_button("Borrow", type="primary")
        if borrow_submit:
            try:
                tx = service.borrow_book(member_id, borrow_book_id.strip())
                st.success("Book borrowed successfully.")
                st.json(tx)
            except Exception as exc:
                st.error(f"Borrow failed: {exc}")


def _render_return_books_panel(service: BaseService, member_id: str) -> None:
    st.subheader("Return Books")

    if st.session_state.get("last_return_msg"):
        st.success(st.session_state.pop("last_return_msg"))
        last_tx = st.session_state.pop("last_return_tx", None)
        if last_tx:
            st.json(last_tx)

    st.caption("Books currently borrowed by this member")
    try:
        result = service.report_member_active_loans(member_id)
        active_loans = result.get("items", [])
    except Exception as exc:
        st.error(f"Unable to load active loans: {exc}")
        return

    if not active_loans:
        st.info("No borrowed books pending return.")
        return

    header = st.columns([2, 4, 2, 2, 1])
    header[0].markdown("**Book ID**")
    header[1].markdown("**Title**")
    header[2].markdown("**Author**")
    header[3].markdown("**Borrowed At**")
    header[4].markdown("**Action**")

    for idx, loan in enumerate(active_loans):
        book = loan.get("book", {})
        book_id = str(book.get("book_id", ""))
        row = st.columns([2, 4, 2, 2, 1])
        row[0].write(book_id or "-")
        row[1].write(book.get("title", "-"))
        row[2].write(book.get("author", "-"))
        row[3].write(loan.get("borrowed_at", "-"))
        if row[4].button(
            "Return",
            key=f"return_active_{member_id}_{book_id}_{idx}",
            type="primary",
        ):
            st.session_state["pending_return"] = {
                "member_id": member_id,
                "book_id": book_id,
                "title": str(book.get("title", "")),
            }
            st.rerun()

    if st.session_state.get("pending_return"):
        _return_confirmation_dialog(service)


def _render_member_detail_view(service: BaseService) -> None:
    member_id = st.session_state.get("selected_member_id")
    member = st.session_state.get("selected_member") or {}

    if st.button("Back to Members"):
        st.session_state["selected_member_id"] = None
        st.session_state["selected_member"] = None
        st.session_state["pending_return"] = None
        st.rerun()

    st.caption(f"Selected member: {member_id}")

    info_tab, history_tab, borrow_tab, return_tab = st.tabs(
        ["Info", "Previous Transactions", "Borrow", "Return Books"]
    )

    with info_tab:
        _render_member_info_panel(member)

    with history_tab:
        _render_member_history_panel(service, member_id)

    with borrow_tab:
        _render_borrow_books_panel(service, member_id)

    with return_tab:
        _render_return_books_panel(service, member_id)


def render_member_tab(service: BaseService) -> None:
    _ensure_member_state()
    if st.session_state.get("selected_member_id"):
        _render_member_detail_view(service)
    else:
        _render_member_list_view(service)

