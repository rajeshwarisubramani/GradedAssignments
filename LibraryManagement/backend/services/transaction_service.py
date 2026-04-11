from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from backend.config.settings import BOOKS_FILE, MEMBER_BOOKS_FILE, MEMBERS_FILE, TRANSACTIONS_FILE
from backend.domain.exceptions import ConflictError, NotFoundError, ValidationError
from backend.utils.json_io import read_json_list, write_json_list

MAX_BORROWED_BOOKS = 5
MAX_BORROW_DAYS = 15
FINE_PER_DAY = 5.0


def _next_transaction_id(transactions: list[dict[str, Any]]) -> str:
	max_id = 0
	for tx in transactions:
		raw = str(tx.get("transaction_id", "")).strip()
		if raw.startswith("T") and raw[1:].isdigit():
			max_id = max(max_id, int(raw[1:]))
	return f"T{max_id + 1:05d}"


def _active_borrow_ids(transactions: list[dict[str, Any]]) -> set[str]:
	borrowed_ids = {
		str(tx.get("transaction_id", "")).strip()
		for tx in transactions
		if str(tx.get("status", "")).strip().lower() == "borrowed"
	}
	returned_ids = {
		str(tx.get("borrow_transaction_id", "")).strip()
		for tx in transactions
		if str(tx.get("status", "")).strip().lower() == "returned"
	}
	borrowed_ids.discard("")
	returned_ids.discard("")
	return borrowed_ids - returned_ids


def build_member_book_indexes(
	rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any] | dict[str, list[dict[str, Any]]]]:
	"""Build O(1) lookup indexes for flat member-book records.

	Returns a dict with:
	- by_id: record lookup by composite id
	- by_member_id: list of records per member_id
	- by_book_id: list of records per book_id
	"""
	if not isinstance(rows, list):
		raise ValidationError("rows must be a list of objects.")

	by_id: dict[str, dict[str, Any]] = {}
	by_member_id: dict[str, list[dict[str, Any]]] = {}
	by_book_id: dict[str, list[dict[str, Any]]] = {}

	for index, row in enumerate(rows):
		if not isinstance(row, dict):
			raise ValidationError(f"rows[{index}] must be an object.")

		record_id = str(row.get("id", "")).strip()
		member_id = str(row.get("member_id", "")).strip()
		book_id = str(row.get("book_id", "")).strip()

		if not record_id or not member_id or not book_id:
			raise ValidationError(
				f"rows[{index}] must include non-empty id, member_id, and book_id."
			)

		if record_id in by_id:
			raise ValidationError(f"Duplicate id found: {record_id}")

		normalized = dict(row)
		normalized["id"] = record_id
		normalized["member_id"] = member_id
		normalized["book_id"] = book_id

		by_id[record_id] = normalized
		by_member_id.setdefault(member_id, []).append(normalized)
		by_book_id.setdefault(book_id, []).append(normalized)

	return {
		"by_id": by_id,
		"by_member_id": by_member_id,
		"by_book_id": by_book_id,
	}


class TransactionService:
	"""JSON-backed transaction service for borrow/return flows."""

	def __init__(
		self,
		transactions_file: Path | None = None,
		books_file: Path | None = None,
		members_file: Path | None = None,
		member_books_file: Path | None = None,
	) -> None:
		self.transactions_file = transactions_file or TRANSACTIONS_FILE
		self.books_file = books_file or BOOKS_FILE
		self.members_file = members_file or MEMBERS_FILE
		self.member_books_file = member_books_file or MEMBER_BOOKS_FILE

	def fetch_all_transactions(self) -> list[dict[str, Any]]:
		return read_json_list(self.transactions_file)

	def fetch_previous_transactions(self, member_id: str, book_id: str) -> list[dict[str, Any]]:
		member_key = member_id.strip()
		book_key = book_id.strip()
		if not member_key or not book_key:
			return []

		return [
			tx
			for tx in self.fetch_all_transactions()
			if str(tx.get("member_id", "")).strip() == member_key
			and str(tx.get("book_id", "")).strip() == book_key
		]

	def _upsert_member_book_row(
		self,
		member_books: list[dict[str, Any]],
		member_id: str,
		book_id: str,
		transaction_id: str,
	) -> None:
		pair_id = f"{member_id}_{book_id}"
		for row in member_books:
			if str(row.get("id", "")).strip() == pair_id:
				tx_ids = row.get("transaction_ids")
				if not isinstance(tx_ids, list):
					tx_ids = []
				tx_ids.append(transaction_id)
				row["transaction_ids"] = tx_ids
				return

		member_books.append(
			{
				"id": pair_id,
				"member_id": member_id,
				"book_id": book_id,
				"transaction_ids": [transaction_id],
			}
		)

	def borrow_book(self, member_id: str, book_id: str, borrow_date: date | None = None) -> dict[str, Any]:
		member_key = member_id.strip()
		book_key = book_id.strip()
		if not member_key or not book_key:
			raise ValidationError("member_id and book_id are required.")

		books = read_json_list(self.books_file)
		members = read_json_list(self.members_file)
		transactions = read_json_list(self.transactions_file)
		member_books = read_json_list(self.member_books_file)

		if not any(str(row.get("member_id", "")).strip() == member_key for row in members):
			raise NotFoundError("Member not found.")

		book = next((row for row in books if str(row.get("book_id", "")).strip() == book_key), None)
		if book is None:
			raise NotFoundError("Book not found.")

		available = int(book.get("available_copies", 0) or 0)
		if available <= 0:
			raise ConflictError("No books available.")

		active_ids = _active_borrow_ids(transactions)
		member_active_count = sum(
			1
			for tx in transactions
			if str(tx.get("transaction_id", "")).strip() in active_ids
			and str(tx.get("member_id", "")).strip() == member_key
		)
		if member_active_count >= MAX_BORROWED_BOOKS:
			raise ConflictError("Member cannot borrow more than 5 books at a time.")

		borrowed_on = borrow_date or date.today()
		due_on = borrowed_on + timedelta(days=MAX_BORROW_DAYS)
		tx_id = _next_transaction_id(transactions)

		transaction = {
			"transaction_id": tx_id,
			"member_id": member_key,
			"book_id": book_key,
			"borrow_date": borrowed_on.isoformat(),
			"due_date": due_on.isoformat(),
			"return_date": None,
			"status": "borrowed",
			"max_borrow_days": MAX_BORROW_DAYS,
		}

		transactions.append(transaction)
		book["available_copies"] = available - 1
		book["status"] = "available" if int(book["available_copies"]) > 0 else "issued"
		self._upsert_member_book_row(member_books, member_key, book_key, tx_id)

		write_json_list(self.transactions_file, transactions)
		write_json_list(self.books_file, books)
		write_json_list(self.member_books_file, member_books)
		return transaction

	def return_book(self, member_id: str, book_id: str, return_date: date | None = None) -> dict[str, Any]:
		member_key = member_id.strip()
		book_key = book_id.strip()
		if not member_key or not book_key:
			raise ValidationError("member_id and book_id are required.")

		books = read_json_list(self.books_file)
		members = read_json_list(self.members_file)
		transactions = read_json_list(self.transactions_file)
		member_books = read_json_list(self.member_books_file)

		if not any(str(row.get("member_id", "")).strip() == member_key for row in members):
			raise NotFoundError("Member not found.")

		book = next((row for row in books if str(row.get("book_id", "")).strip() == book_key), None)
		if book is None:
			raise NotFoundError("Book not found.")

		total = int(book.get("total_copies", 0) or 0)
		available = int(book.get("available_copies", 0) or 0)
		if available >= total:
			raise ConflictError("Invalid return: all copies are already available.")

		active_ids = _active_borrow_ids(transactions)
		candidates = [
			tx
			for tx in transactions
			if str(tx.get("transaction_id", "")).strip() in active_ids
			and str(tx.get("member_id", "")).strip() == member_key
			and str(tx.get("book_id", "")).strip() == book_key
			and str(tx.get("status", "")).strip().lower() == "borrowed"
		]
		if not candidates:
			raise NotFoundError("No active borrow transaction found for this member and book.")

		borrow_tx = candidates[-1]
		due_raw = str(borrow_tx.get("due_date", "")).strip()
		try:
			due_on = date.fromisoformat(due_raw)
		except ValueError as exc:
			raise ValidationError("Borrow transaction due_date is invalid.") from exc

		returned_on = return_date or date.today()
		days_overdue = max((returned_on - due_on).days, 0)
		is_delayed = days_overdue > 0
		tx_id = _next_transaction_id(transactions)

		return_tx = {
			"transaction_id": tx_id,
			"borrow_transaction_id": str(borrow_tx.get("transaction_id", "")).strip(),
			"member_id": member_key,
			"book_id": book_key,
			"borrow_date": str(borrow_tx.get("borrow_date", "")).strip(),
			"due_date": due_on.isoformat(),
			"return_date": returned_on.isoformat(),
			"status": "returned",
			"max_borrow_days": MAX_BORROW_DAYS,
			"delay_info": {
				"is_delayed": is_delayed,
				"days_overdue": days_overdue,
				"return_date_actual": returned_on.isoformat() if is_delayed else None,
				"fine_per_day": float(FINE_PER_DAY),
				"total_fine": float(days_overdue * FINE_PER_DAY),
			},
		}

		transactions.append(return_tx)
		book["available_copies"] = min(total, available + 1)
		book["status"] = "available" if int(book["available_copies"]) > 0 else "issued"
		self._upsert_member_book_row(member_books, member_key, book_key, tx_id)

		write_json_list(self.transactions_file, transactions)
		write_json_list(self.books_file, books)
		write_json_list(self.member_books_file, member_books)
		return return_tx


