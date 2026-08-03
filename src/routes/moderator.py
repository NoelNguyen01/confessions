from src.controller.moderator import check_confession_controller
from flask import Blueprint
from os import getenv

censor_bp = Blueprint("censor", __name__)


@censor_bp.route("/check/<api_key>", methods=["POST"])
def check_confession_route(api_key):
    if api_key != getenv("YOUR_KEY", None):
        return {"success": False, "message": "authentication failed"}, 401
    return check_confession_controller()
