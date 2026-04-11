from __future__ import annotations

import streamlit as st

try:
    from .service import BaseService
    from .templates import render_member_tab
except ImportError:
    # Supports `streamlit run frontend/streamlit_app/app.py` script execution.
    from service import BaseService
    from templates import render_member_tab


def _inject_dark_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f8fbff;
            color: #0f172a;
        }

        h1, h2, h3, p, label, div {
            color: #0f172a;
        }

        [data-testid="stHeader"] {
            background: rgba(255, 255, 255, 0.96);
            border-bottom: 1px solid #dbeafe;
        }

        [data-testid="stSidebar"] {
            background-color: #eff6ff;
        }

        div[data-testid="stInfo"] {
            background-color: #eff6ff;
            border: 1px solid #bfdbfe;
            color: #1e3a8a;
        }

        div[data-testid="stButton"] > button {
            border-radius: 8px;
            font-weight: 600;
        }

        button[kind="primary"] {
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            border: 1px solid #1d4ed8;
            color: #ffffff;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
        }

        button[kind="primary"]:hover {
            background: linear-gradient(135deg, #60a5fa, #3b82f6);
            border-color: #2563eb;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _get_service() -> BaseService:
    if "api_service" not in st.session_state:
        st.session_state["api_service"] = BaseService()
    return st.session_state["api_service"]


def main() -> None:
    st.set_page_config(page_title="Library Management", layout="wide")
    _inject_dark_theme()
    service = _get_service()


    st.title("Library Management")
    st.caption("Home page")

    member_tab, book_tab, transaction_tab, report_tab = st.tabs(
        ["Member Info", "Book Info", "Book Transaction", "Report"]
    )

    with member_tab:
        render_member_tab(service)

    with book_tab:
        st.subheader("Book Info")
        st.info("This page is intentionally empty for now.")

    with transaction_tab:
        st.subheader("Book Transaction")
        st.info("This page is intentionally empty for now.")

    with report_tab:
        st.subheader("Report")
        st.info("This page is intentionally empty for now.")


if __name__ == "__main__":
    main()

