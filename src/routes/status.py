from flask import Blueprint
from os import getenv

status_bp = Blueprint("status", __name__)


@status_bp.route("/status/<api_key>", methods=["GET"])
def check_status(api_key):
    key_system = str(getenv("YOUR_KEY", ""))
    if key_system != str(api_key):
        return {"message": "invalid key", "success": False}, 401

    env_vars = [
        "MONGO_URI", "PAGE_ID", "ACCESS_TOKEN", "YOUR_KEY",
        "SHEET_NAME", "CONFESSION_QUESTION", "EMAIL_QUESTION",
        "GOOGLE_AI_API_KEY", "AI_MODEL_NAME", "GOOGLE_CREDENTIALS_JSON"
    ]

    status = {}
    for var in env_vars:
        val = getenv(var)
        if val:
            if var in ("ACCESS_TOKEN", "GOOGLE_AI_API_KEY", "MONGO_URI", "GOOGLE_CREDENTIALS_JSON"):
                status[var] = f"✅ Đã cài ({val[:15]}...)"
            else:
                status[var] = f"✅ {val}"
        else:
            status[var] = "❌ CHƯA CÀI!"

    return {"status": status, "success": True}, 200
