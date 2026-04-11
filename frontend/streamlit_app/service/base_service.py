"""HTTP client wrapper for calling the library backend APIs."""

from __future__ import annotations

from typing import Any

import requests

from .api_info import API_PATHS, DEFAULT_BASE_URL


class BaseService:
    """Small API client used by frontend apps."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: int = 10,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.get(
            self._build_url(path), params=params, timeout=self.timeout_seconds
        )
        return self._parse_response(response)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            self._build_url(path), json=payload, timeout=self.timeout_seconds
        )
        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: requests.Response) -> dict[str, Any]:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            message = response.text.strip() or str(exc)
            raise RuntimeError(f"API request failed: {message}") from exc

        body = response.json() if response.text else {}
        if isinstance(body, dict):
            return body
        return {"items": body}

    def close(self) -> None:
        self.session.close()

    def health(self) -> dict[str, Any]:
        return self._get(API_PATHS["health"])

    def list_books(self) -> dict[str, Any]:
        return self._get(API_PATHS["books"])

    def add_book(
        self,
        book_id: str,
        title: str,
        author: str,
        genre: str,
    ) -> dict[str, Any]:
        return self._post(
            API_PATHS["books"],
            {
                "book_id": book_id,
                "title": title,
                "author": author,
                "genre": genre,
            },
        )

    def list_members(self) -> dict[str, Any]:
        return self._get(API_PATHS["members"])

    def add_member(
        self,
        member_id: str,
        name: str,
        age: int,
        contact_info: str,
    ) -> dict[str, Any]:
        return self._post(
            API_PATHS["members"],
            {
                "member_id": member_id,
                "name": name,
                "age": age,
                "contact_info": contact_info,
            },
        )

    def borrow_book(self, member_id: str, book_id: str) -> dict[str, Any]:
        return self._post(
            API_PATHS["borrow"],
            {"member_id": member_id, "book_id": book_id},
        )

    def return_book(self, member_id: str, book_id: str) -> dict[str, Any]:
        return self._post(
            API_PATHS["return"],
            {"member_id": member_id, "book_id": book_id},
        )

    def report_available_by_genre(self, genre: str) -> dict[str, Any]:
        reports = API_PATHS["reports"]
        return self._get(reports["available_by_genre"], {"genre": genre})

    def report_members_with_borrowed_books(self) -> dict[str, Any]:
        reports = API_PATHS["reports"]
        return self._get(reports["members_with_borrowed_books"])

    def report_most_popular_genre(self) -> dict[str, Any]:
        reports = API_PATHS["reports"]
        return self._get(reports["most_popular_genre"])

    def report_book_history(self, book_id: str) -> dict[str, Any]:
        reports = API_PATHS["reports"]
        return self._get(reports["book_history"], {"book_id": book_id})

    def report_member_history(self, member_id: str) -> dict[str, Any]:
        reports = API_PATHS["reports"]
        return self._get(reports["member_history"], {"member_id": member_id})

    def report_member_active_loans(self, member_id: str) -> dict[str, Any]:
        reports = API_PATHS["reports"]
        return self._get(reports["member_active_loans"], {"member_id": member_id})

