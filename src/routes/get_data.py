from flask import Blueprint
from src.controller.get_data import submit_confession

data_bp = Blueprint("get_data", __name__)


@data_bp.route("/submit", methods=["POST"])
def handle_form():
    return submit_confession()
