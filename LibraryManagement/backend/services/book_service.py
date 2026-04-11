from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from backend.config.settings import BOOKS_FILE
from backend.domain.exceptions import NotFoundError, ValidationError
from backend.utils.json_io import read_json_list, write_json_list


class BookService:
	"""Pandas-backed service for optimized book catalog and inventory updates."""

	_COLUMNS = [
		"book_id",
		"title",
		"author",
		"isbn",
		"genre",
		"publication_year",
		"total_copies",
		"available_copies",
		"status",
	]

	def __init__(self, file_path: Path | None = None) -> None:
		self.file_path = file_path or BOOKS_FILE

	def _load_dataframe(self) -> pd.DataFrame:
		"""Load books.json into a normalized DataFrame with consistent dtypes."""
		rows = read_json_list(self.file_path)
		frame = pd.DataFrame(rows)

		for column in self._COLUMNS:
			if column not in frame.columns:
				frame[column] = None

		frame["book_id"] = frame["book_id"].fillna("").astype(str)
		frame["title"] = frame["title"].fillna("").astype(str)
		frame["author"] = frame["author"].fillna("").astype(str)
		frame["isbn"] = frame["isbn"].fillna("").astype(str)
		frame["genre"] = frame["genre"].fillna("").astype(str)
		frame["publication_year"] = pd.to_numeric(frame["publication_year"], errors="coerce").fillna(0).astype(int)
		frame["total_copies"] = pd.to_numeric(frame["total_copies"], errors="coerce").fillna(1).astype(int)
		frame["available_copies"] = pd.to_numeric(frame["available_copies"], errors="coerce").fillna(1).astype(int)
		frame["status"] = frame["status"].fillna("available").astype(str).str.lower()

		frame["total_copies"] = frame["total_copies"].clip(lower=1)
		frame["available_copies"] = frame[["available_copies", "total_copies"]].min(axis=1).clip(lower=0)
		frame["status"] = frame["available_copies"].apply(lambda qty: "available" if qty > 0 else "issued")

		return frame[self._COLUMNS]

	def _persist_dataframe(self, frame: pd.DataFrame) -> None:
		"""Persist DataFrame records back to books.json."""
		write_json_list(self.file_path, frame.to_dict(orient="records"))

	def _next_book_id(self, frame: pd.DataFrame) -> str:
		numeric_ids = pd.to_numeric(frame["book_id"].str.extract(r"^(?:B)?(\d+)$")[0], errors="coerce")
		max_id = int(numeric_ids.max()) if not numeric_ids.isna().all() else 0
		return f"B{(max_id + 1):04d}"

	def fetch_all_books(self) -> list[dict[str, Any]]:
		"""Return all books."""
		frame = self._load_dataframe()
		return frame.to_dict(orient="records")

	def fetch_books_by_name(self, title: str) -> list[dict[str, Any]]:
		"""Return exact-title matches (case-insensitive) as an array."""
		target = title.strip().lower()
		if not target:
			return []

		frame = self._load_dataframe()
		matches = frame[frame["title"].str.lower() == target]
		return matches.to_dict(orient="records")

	def fetch_book_by_id(self, book_id: str) -> dict[str, Any] | None:
		"""Return one book by id, or None if not found."""
		key = book_id.strip()
		if not key:
			return None

		frame = self._load_dataframe()
		matches = frame[frame["book_id"] == key]
		if matches.empty:
			return None
		return matches.iloc[0].to_dict()

	def add_book(
		self,
		title: str,
		author: str,
		genre: str,
		publication_year: int,
		isbn: str = "",
		copies: int = 1,
	) -> dict[str, Any]:
		"""Add a new title or increase inventory by ISBN / title+year matching rules."""
		if not all(v and str(v).strip() for v in (title, author, genre)):
			raise ValidationError("title, author, and genre are required.")

		try:
			year = int(publication_year)
		except (TypeError, ValueError) as exc:
			raise ValidationError("publication_year must be an integer.") from exc

		try:
			qty = int(copies)
		except (TypeError, ValueError) as exc:
			raise ValidationError("copies must be an integer.") from exc

		if qty <= 0:
			raise ValidationError("copies must be greater than 0.")

		normalized_isbn = isbn.strip()
		normalized_title = title.strip()
		frame = self._load_dataframe()

		if normalized_isbn:
			mask = frame["isbn"] == normalized_isbn
		else:
			mask = (frame["title"].str.lower() == normalized_title.lower()) & (frame["publication_year"] == year)

		if mask.any():
			frame.loc[mask, "total_copies"] = frame.loc[mask, "total_copies"] + qty
			frame.loc[mask, "available_copies"] = frame.loc[mask, "available_copies"] + qty
			frame.loc[mask, "status"] = "available"
			self._persist_dataframe(frame)
			return frame.loc[mask].iloc[0].to_dict()

		new_row = {
			"book_id": self._next_book_id(frame),
			"title": normalized_title,
			"author": author.strip(),
			"isbn": normalized_isbn,
			"genre": genre.strip(),
			"publication_year": year,
			"total_copies": qty,
			"available_copies": qty,
			"status": "available",
		}
		frame = pd.concat([frame, pd.DataFrame([new_row])], ignore_index=True)
		self._persist_dataframe(frame)
		return new_row

	def update_available_copies_on_return(self, book_id: str, returned_copies: int = 1) -> dict[str, Any]:
		"""Increase available copies when books are returned, capped at total copies."""
		key = book_id.strip()
		if not key:
			raise ValidationError("book_id is required.")

		try:
			qty = int(returned_copies)
		except (TypeError, ValueError) as exc:
			raise ValidationError("returned_copies must be an integer.") from exc

		if qty <= 0:
			raise ValidationError("returned_copies must be greater than 0.")

		frame = self._load_dataframe()
		mask = frame["book_id"] == key
		if not mask.any():
			raise NotFoundError("Book not found.")

		frame.loc[mask, "available_copies"] = (
			frame.loc[mask, "available_copies"] + qty
		).clip(upper=frame.loc[mask, "total_copies"])
		frame.loc[mask, "status"] = frame.loc[mask, "available_copies"].apply(
			lambda value: "available" if int(value) > 0 else "issued"
		)

		self._persist_dataframe(frame)
		return frame.loc[mask].iloc[0].to_dict()

