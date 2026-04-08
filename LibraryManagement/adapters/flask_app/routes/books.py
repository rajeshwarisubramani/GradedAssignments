from flask import Blueprint, current_app, request

books_bp = Blueprint("books", __name__, url_prefix="/books")


@books_bp.get("")
def list_books():
    service = current_app.config["library_service"]
    return {"items": service.list_books()}


@books_bp.post("")
def add_book():
    payload = request.get_json(silent=True) or {}
    service = current_app.config["library_service"]
    book = service.add_book(
        payload.get("book_id", ""),
        payload.get("title", ""),
        payload.get("author", ""),
        payload.get("genre", ""),
    )
    return book, 201

