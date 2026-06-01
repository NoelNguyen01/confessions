from src.controller.moderator import check_confession_controller
from flask import Blueprint
from os import getenv

censor_bp = Blueprint("censor", __name__)


@censor_bp.route("/check/<api_key>", methods=["POST"])
def check_confession_route(api_key):
    return (
        check_confession_controller()
        if api_key == getenv("YOUR_KEY", None)
        else {"success": False, "message": "authentication failed"}
    )
