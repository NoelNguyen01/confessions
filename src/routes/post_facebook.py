from flask import Blueprint
from os import getenv
from src.controller.post_facebook import post_facebook

post_bp = Blueprint("post_to_facebook", __name__)


@post_bp.route("/post/<api_key>", methods=["POST"])
def post_to_facebook(api_key):
    key_system = str(getenv("YOUR_KEY"))

    if key_system == api_key:
        return post_facebook()
    return "hahahaha", 401
