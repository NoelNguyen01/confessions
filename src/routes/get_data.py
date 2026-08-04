from flask import Blueprint, request
from src.controller.get_data import get_data_sheet
from os import getenv

data_bp = Blueprint("get_data", __name__)


@data_bp.route("/submit", methods=["POST"])
@data_bp.route("/submit/<api_key>", methods=["POST"])
def handle_form(api_key=None):
    key_system = str(getenv("YOUR_KEY"))

    if api_key is None:
        body = request.get_json(silent=True) or {}
        api_key = body.get("your_key") or body.get("api_key")

    if key_system == str(api_key):
        return get_data_sheet()
    return {"message": "invalid verification code", "success": False}, 401
