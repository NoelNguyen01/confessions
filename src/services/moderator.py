from google.genai.errors import APIError
from config import Config
from src.extension.google_ai import client
from src.utils.extract_json import extract_json
from src.prompt.moderation import _return_prompt_from_list_cfs
from src.extension.db import db
from datetime import datetime

# TODO: How the hell can you set the active status to true when that status only shows "upload completed"???


def chat_main_ai(ai_model: str, content_input: str, confession_input: str = "") -> str:
    models_to_try = [ai_model, "gemini-2.5-flash", "gemini-2.0-flash"]
    seen = set()
    models_to_try = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=content_input + confession_input,
            )
            if response and response.text:
                return response.text
        except Exception as e:
            print(f"⚠️ Gemini model {model_name} error: {e}", flush=True)

    return ""


def _get_check_confession():
    try:
        collection = db.confession_data

        _id = list(collection.find(
            {"active": False}, {"Confession": 1, "_id": 0, "status": 1, "id": 1}
        ))

        if not _id:
            return {
                "success": False,
                "message": "An error occurred while retrieving the data or no active=False data",
            }

        _list = {}
        for user in _id:
            status = user.get("status", None)
            if not status and user.get("Confession"):
                _list[user.get("Confession")] = user.get("id", "")

        if not _list:
            return {"success": True, "message": "No confessions need censorship"}

        _message = _return_prompt_from_list_cfs(**_list)

        _result_ai = chat_main_ai(
            ai_model=Config.AI_MODEL_NAME,
            confession_input=str(_message),
            content_input="",
        )

        if not _result_ai:
            print("⚠️ AI không trả về kết quả kiểm duyệt (bỏ qua bước AI).", flush=True)
            return {"success": False, "message": "AI returned empty response"}

        json_data = extract_json(_result_ai)
        if not json_data or not isinstance(json_data, list):
            print(f"⚠️ Không thể parse JSON từ kết quả AI: {_result_ai[:100]}", flush=True)
            return {"success": False, "message": "Failed to parse AI JSON"}

        for _result in json_data:
            if not isinstance(_result, dict):
                continue
            _id_find = _result.get("id_origin")
            _result.pop("id_origin", None)
            _result["check_time"] = datetime.now()

            collection.update_one(
                {"id": _id_find},
                {"$set": {"data_ai_result": _result, "censored": True}},
            )

        return {"success": True, "message": "Successful censorship", "data": json_data}
    except Exception as e:
        print(f"❌ Error in _get_check_confession: {e}", flush=True)
        return {"success": False, "message": str(e)}
