from flask import Blueprint
from src.controller.get_data import get_data_sheet
from os import getenv

data_bp = Blueprint("get_data", __name__)


@data_bp.route("/submit/<api_key>", methods=["POST"])
def handle_form(api_key):
    key_system = str(getenv("YOUR_KEY"))
    if key_system == str(api_key):
        return get_data_sheet()
    return {"message": "invalid verification code", "success": False}, 401
