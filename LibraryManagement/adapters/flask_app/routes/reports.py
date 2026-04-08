from flask import Blueprint, current_app, request

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.get("/available-by-genre")
def available_by_genre():
    genre = request.args.get("genre", "")
    service = current_app.config["library_service"]
    return {"items": service.report_available_books_by_genre(genre)}


@reports_bp.get("/members-with-borrowed-books")
def members_with_borrowed_books():
    service = current_app.config["library_service"]
    return {"items": service.report_members_with_borrowed_books()}


@reports_bp.get("/most-popular-genre")
def most_popular_genre():
    service = current_app.config["library_service"]
    return service.report_most_popular_genre()

@reports_bp.get("/book-history")
def book_history():
    book_id = request.args.get("book_id", "")
    service = current_app.config["library_service"]
    return {"book_id": book_id, "items": service.report_book_history(book_id)}


@reports_bp.get("/member-history")
def member_history():
    member_id = request.args.get("member_id", "")
    service = current_app.config["library_service"]
    return {"member_id": member_id, "items": service.report_member_history(member_id)}