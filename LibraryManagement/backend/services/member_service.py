from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from backend.config.settings import MEMBERS_FILE
from backend.domain.exceptions import ConflictError, NotFoundError, ValidationError
from backend.utils.json_io import read_json_list, write_json_list


class MemberService:
    """Pandas-backed member service for fast filtering and updates."""

    _COLUMNS = [
        "member_id",
        "name",
        "email",
        "phone",
        "membership_date",
        "status",
        "address",
    ]

    def __init__(self, file_path: Path | None = None) -> None:
        """Configure the members data file path."""
        self.file_path = file_path or MEMBERS_FILE

    def _load_dataframe(self) -> pd.DataFrame:
        """Load members into a normalized DataFrame with expected columns."""
        rows = read_json_list(self.file_path)
        frame = pd.DataFrame(rows)

        for column in self._COLUMNS:
            if column not in frame.columns:
                frame[column] = None

        # Backward compatibility for older records using contact_info.
        if "contact_info" in frame.columns:
            frame["email"] = frame["email"].fillna(frame["contact_info"])

        frame["member_id"] = frame["member_id"].fillna("").astype(str)
        frame["name"] = frame["name"].fillna("").astype(str)
        frame["email"] = frame["email"].fillna("").astype(str)
        frame["phone"] = frame["phone"].fillna("").astype(str)
        frame["membership_date"] = frame["membership_date"].fillna("").astype(str)
        frame["status"] = frame["status"].fillna("active").astype(str).str.lower()
        frame["address"] = frame["address"].apply(lambda value: value if isinstance(value, dict) else {})

        return frame[self._COLUMNS]

    def _persist_dataframe(self, frame: pd.DataFrame) -> None:
        """Persist a DataFrame back to members.json as a list of records."""
        write_json_list(self.file_path, frame.to_dict(orient="records"))

    def fetch_all_members(self) -> list[dict[str, Any]]:
        """Return all members from the JSON store."""
        frame = self._load_dataframe()
        return frame.to_dict(orient="records")

    def fetch_members_by_name(self, name: str) -> list[dict[str, Any]]:
        """Return all members whose name exactly matches (case-insensitive)."""
        target = name.strip().lower()
        if not target:
            return []

        frame = self._load_dataframe()
        matches = frame[frame["name"].str.lower() == target]
        return matches.to_dict(orient="records")

    def fetch_member_by_id(self, member_id: str) -> dict[str, Any] | None:
        """Return one member by id, or None when no match exists."""
        key = member_id.strip()
        if not key:
            return None

        frame = self._load_dataframe()
        matches = frame[frame["member_id"] == key]
        if matches.empty:
            return None
        return matches.iloc[0].to_dict()

    def add_member(
        self,
        member_id: str,
        name: str,
        email: str,
        phone: str,
        status: str = "active",
        address: dict | None = None,
    ) -> dict[str, Any]:
        """Create a member and auto-fill membership_date with today's date."""
        if not all(v and str(v).strip() for v in (member_id, name, email, phone)):
            raise ValidationError("member_id, name, email, and phone are required.")

        frame = self._load_dataframe()
        key = member_id.strip()
        if (frame["member_id"] == key).any():
            raise ConflictError("Member ID already exists.")

        # membership_date is always created from the transaction date.
        member = {
            "member_id": key,
            "name": name.strip(),
            "email": email.strip(),
            "phone": phone.strip(),
            "membership_date": date.today().isoformat(),
            "status": (status or "active").strip().lower(),
            "address": address if isinstance(address, dict) else {},
        }

        frame = pd.concat([frame, pd.DataFrame([member])], ignore_index=True)
        self._persist_dataframe(frame)
        return member

    def update_member(self, member_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update mutable member fields and return the refreshed record."""
        key = member_id.strip()
        if not key:
            raise ValidationError("member_id is required.")

        frame = self._load_dataframe()
        mask = frame["member_id"] == key
        if not mask.any():
            raise NotFoundError("Member not found.")

        # Prevent id mutation and only allow known update fields.
        safe_updates = dict(updates)
        safe_updates.pop("member_id", None)

        for field in ("name", "email", "phone", "membership_date", "status", "address"):
            if field not in safe_updates:
                continue
            value = safe_updates[field]
            if field == "status":
                value = (value or "active").strip().lower()
            if field == "address" and not isinstance(value, dict):
                value = {}
            if field in {"name", "email", "phone", "membership_date"}:
                value = "" if value is None else str(value).strip()
            frame.loc[mask, field] = [value]

        self._persist_dataframe(frame)
        return frame.loc[mask].iloc[0].to_dict()

