from google.genai.errors import APIError
from config import Config
from src.extension.google_ai import client
from src.utils.extract_json import extract_json
from src.prompt.moderation import _return_prompt_from_list_cfs
from src.extension.db import db
from datetime import datetime


def chat_main_ai(ai_model: str, content_input: str, confession_input: str = "") -> str:
    """
    Gọi API Gemini với nhiều model fallback, kiểm tra chi tiết lỗi API / Safety settings.
    """
    models_to_try = [ai_model, "gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-flash-lite"]
    seen = set()
    models_to_try = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

    full_prompt = (content_input + "\n" + confession_input).strip()
    if not full_prompt:
        print("⚠️ [Gemini AI] Prompt rỗng, bỏ qua gọi AI.", flush=True)
        return ""

    for model_name in models_to_try:
        print(f"🤖 [Gemini AI] Thử gọi model: '{model_name}'...", flush=True)
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
            )

            if not response:
                print(f"⚠️ [Gemini AI] Model '{model_name}' trả về response None.", flush=True)
                continue

            # Kiểm tra candidates & safety settings
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, "finish_reason", None)
                if finish_reason and str(finish_reason).upper() in ("SAFETY", "RECITATION", "BLOCKLIST"):
                    print(f"⚠️ [Gemini AI Safety] Model '{model_name}' bị chặn bởi Safety Filter! Finish reason: {finish_reason}", flush=True)
                    if hasattr(candidate, "safety_ratings"):
                        print(f"   Detailed Safety Ratings: {candidate.safety_ratings}", flush=True)
                    continue

            # Thử lấy text an toàn (tránh văng ValueError khi text bị rỗng hoặc suppressed)
            text_result = None
            try:
                text_result = response.text
            except Exception as txt_err:
                print(f"⚠️ [Gemini AI] Lỗi lấy response.text từ model '{model_name}': {txt_err}", flush=True)

            if text_result and text_result.strip():
                print(f"✅ [Gemini AI] Model '{model_name}' phản hồi thành công ({len(text_result)} chars).", flush=True)
                return text_result.strip()
            else:
                print(f"⚠️ [Gemini AI] Model '{model_name}' trả về response text rỗng.", flush=True)

        except APIError as api_err:
            code = getattr(api_err, "code", getattr(api_err, "status_code", "UNKNOWN"))
            print(f"❌ [Gemini APIError] Model '{model_name}' lỗi (Code {code}): {api_err.message if hasattr(api_err, 'message') else api_err}", flush=True)
        except Exception as e:
            err_code = getattr(e, "code", getattr(e, "status_code", None))
            code_str = f" (Status Code: {err_code})" if err_code else ""
            print(f"❌ [Gemini Exception] Model '{model_name}' thất bại{code_str}: [{type(e).__name__}] {e}", flush=True)

    print("❌ [Gemini AI] Tất cả các model AI đều thất bại hoặc bị chặn nội dung.", flush=True)
    return ""


def _get_check_confession():
    """
    Thực hiện kiểm duyệt Confession bằng Gemini AI với chi tiết logging & fallback an toàn.
    """
    try:
        collection = db.confession_data

        _id = list(collection.find(
            {"active": False}, {"Confession": 1, "_id": 0, "status": 1, "id": 1}
        ))

        if not _id:
            return {
                "success": False,
                "message": "Không tìm thấy dữ liệu confession cần kiểm duyệt (hoặc active=True toàn bộ)",
            }

        _list = {}
        for user in _id:
            status = user.get("status", None)
            if not status and user.get("Confession"):
                _list[user.get("Confession")] = user.get("id", "")

        if not _list:
            return {"success": True, "message": "No confessions need censorship"}

        _message = _return_prompt_from_list_cfs(_list)

        _result_ai = chat_main_ai(
            ai_model=Config.AI_MODEL_NAME,
            confession_input=str(_message),
            content_input="",
        )

        if not _result_ai:
            print("⚠️ [AI Moderation] AI không trả về kết quả. Kích hoạt Fallback an toàn...", flush=True)
            fallback_data = []
            for cfs_text, cfs_id in _list.items():
                fallback_item = {
                    "id_origin": cfs_id,
                    "score": 100.0,
                    "reason": "AI Moderation unavailable/blocked; fallback auto-passed",
                    "propose": "APPROVE",
                    "origin_text": cfs_text,
                    "uncertain": False,
                    "check_time": datetime.now()
                }
                collection.update_one(
                    {"id": cfs_id},
                    {"$set": {"data_ai_result": fallback_item, "censored": True, "ai_fallback": True}}
                )
                fallback_data.append(fallback_item)

            return {
                "success": False,
                "message": "AI returned empty response (fallback applied)",
                "fallback_applied": True,
                "data": fallback_data
            }

        json_data = extract_json(_result_ai)
        if not json_data or not isinstance(json_data, list):
            print(f"⚠️ [AI Moderation] Không thể parse JSON từ AI output: {_result_ai[:200]}", flush=True)
            return {
                "success": False,
                "message": "Failed to parse AI JSON response",
                "raw_ai_response": _result_ai[:500]
            }

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
        print(f"❌ Error in _get_check_confession: [{type(e).__name__}] {e}", flush=True)
        return {"success": False, "message": f"Moderation Exception: {str(e)}"}

