from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
BOOKS_FILE = DATA_DIR / "books.json"
MEMBERS_FILE = DATA_DIR / "members.json"
TRANSACTIONS_FILE = DATA_DIR / "transactions.json"


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for file_path in (BOOKS_FILE, MEMBERS_FILE, TRANSACTIONS_FILE):
        if not file_path.exists():
            file_path.write_text("[]", encoding="utf-8")

