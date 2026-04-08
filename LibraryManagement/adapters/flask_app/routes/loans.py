from flask import Blueprint, current_app, request

loans_bp = Blueprint("loans", __name__)


@loans_bp.post("/borrow")
def borrow_book():
    payload = request.get_json(silent=True) or {}
    service = current_app.config["library_service"]
    tx = service.borrow_book(payload.get("member_id", ""), payload.get("book_id", ""))
    return tx, 201


@loans_bp.post("/return")
def return_book():
    payload = request.get_json(silent=True) or {}
    service = current_app.config["library_service"]
    tx = service.return_book(payload.get("member_id", ""), payload.get("book_id", ""))
    return tx, 201

