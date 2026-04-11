# LibraryManagement

## BookService (Pandas)

`backend/services/book_service.py` provides DataFrame-based operations over `data/books.json`:

- fetch all books
- fetch books by exact name (case-insensitive) and return an array
- fetch one book by `book_id`
- add new books with inventory upsert rules:
  - if `isbn` exists, increase `total_copies` and `available_copies`
  - if `isbn` is empty and `title + publication_year` matches, increase copies
  - otherwise add a new book object
- update available copies when a book is returned (capped at total copies)

## Quick Test

```powershell
python -u -m pytest tests/backend/test_book_service.py -q
```

