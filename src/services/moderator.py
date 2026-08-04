from google.genai.errors import APIError
from config import Config
from src.extension.google_ai import client
from src.utils.extract_json import extract_json
from src.prompt.moderation import _return_prompt_from_list_cfs
from src.extension.db import db
from datetime import datetime


def chat_main_ai(ai_model: str, content_input: str, confession_input: str = "") -> str:
    """
    Gọi API Gemini với thứ tự ưu tiên các model ít bị Rate Limit (gemini-2.0-flash-lite, gemini-1.5-flash-8b),
    hỗ trợ fallback Groq API nếu có GROQ_API_KEY.
    """
    # Thứ tự ưu tiên các model ít bị rate limit / quota
    models_to_try = [
        ai_model,
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash"
    ]
    seen = set()
    models_to_try = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

    full_prompt = (content_input + "\n" + confession_input).strip()
    if not full_prompt:
        print("⚠️ [AI Moderation] Prompt rỗng, bỏ qua gọi AI.", flush=True)
        return ""

    for model_name in models_to_try:
        print(f"🤖 [AI Moderation] Thử gọi Gemini Model: '{model_name}'...", flush=True)
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

            # Lấy text phản hồi
            text_result = None
            try:
                text_result = response.text
            except Exception as txt_err:
                print(f"⚠️ [Gemini AI] Lỗi lấy response.text từ model '{model_name}': {txt_err}", flush=True)

            if text_result and text_result.strip():
                print(f"✅ [Gemini AI] Model '{model_name}' kiểm duyệt thành công ({len(text_result)} chars).", flush=True)
                return text_result.strip()
            else:
                print(f"⚠️ [Gemini AI] Model '{model_name}' trả về text rỗng.", flush=True)

        except APIError as api_err:
            code = getattr(api_err, "code", getattr(api_err, "status_code", "UNKNOWN"))
            msg = api_err.message if hasattr(api_err, "message") else str(api_err)
            if "429" in str(code) or "QUOTA" in msg.upper() or "EXHAUSTED" in msg.upper():
                print(f"⚠️ [Gemini Rate Limit 429] Model '{model_name}' bị hết Quota/Rate Limit. Chuyển sang model tiếp theo...", flush=True)
            else:
                print(f"❌ [Gemini APIError] Model '{model_name}' lỗi (Code {code}): {msg}", flush=True)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Quota" in err_str:
                print(f"⚠️ [Gemini Rate Limit 429] Model '{model_name}' bị vượt giới hạn request (Rate Limit). Thử model khác...", flush=True)
            else:
                print(f"❌ [Gemini Exception] Model '{model_name}' thất bại: [{type(e).__name__}] {e}", flush=True)

    # Nếu Gemini hết Quota & có cấu hình GROQ_API_KEY -> Thử gọi Groq API (Miễn phí, không bị limit)
    if Config.groq_api_key:
        print("🤖 [AI Fallback] Gọi Groq API (llama-3.3-70b-versatile)...", flush=True)
        try:
            import urllib.request
            import json
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {Config.groq_api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0"
                },
                data=json.dumps({
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": full_prompt}],
                    "response_format": {"type": "json_object"}
                }).encode('utf-8')
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                res_body = json.loads(resp.read().decode('utf-8'))
                groq_text = res_body['choices'][0]['message']['content']
                if groq_text:
                    print("✅ [Groq AI] Phản hồi kiểm duyệt thành công từ Groq API!", flush=True)
                    return groq_text.strip()
        except Exception as groq_err:
            print(f"⚠️ [Groq AI Error] Lỗi gọi Groq API: {groq_err}", flush=True)

    print("❌ [AI Moderation] Tất cả các model AI đều bị Rate Limit hoặc lỗi. Bật chế độ Auto-Approve Fallback.", flush=True)
    return ""


def _get_check_confession():
    """
    Thực hiện kiểm duyệt Confession bằng AI với chi tiết logging & fallback an toàn.
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
            print("⚠️ [AI Moderation] AI bị giới hạn/rỗng. Tự động Auto-Approve để tiếp tục sang Bước Đăng Facebook...", flush=True)
            fallback_data = []
            for cfs_text, cfs_id in _list.items():
                fallback_item = {
                    "id_origin": cfs_id,
                    "score": 100.0,
                    "reason": "AI Rate Limited; Auto-passed to allow Facebook posting",
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
                "success": True,
                "message": "AI rate limited (Auto-approved fallback applied)",
                "fallback_applied": True,
                "data": fallback_data
            }

        json_data = extract_json(_result_ai)
        if isinstance(json_data, dict):
            json_data = [json_data]
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


