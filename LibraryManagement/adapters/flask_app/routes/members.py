from flask import Blueprint, current_app, request

members_bp = Blueprint("members", __name__, url_prefix="/members")


@members_bp.get("")
def list_members():
    service = current_app.config["library_service"]
    return {"items": service.list_members()}


@members_bp.post("")
def add_member():
    payload = request.get_json(silent=True) or {}
    service = current_app.config["library_service"]
    member = service.register_member(
        payload.get("member_id", ""),
        payload.get("name", ""),
        payload.get("age", 0),
        payload.get("contact_info", ""),
    )
    return member, 201

