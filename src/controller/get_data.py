import gspread
from src.services.get_data import _get_sheet, _fetch_latest_entry, _save_confession
from src.utils.logger import logger
from os import getenv
from src.extension.db import db


def get_data_sheet() -> dict:
    try:
        sheet = _get_sheet()
        latest_entry = _fetch_latest_entry(sheet)

        if not latest_entry:
            return {"message": "Sheet has no data", "success": False, "data": []}, 404

        confession = latest_entry.get(str(getenv("CONFESSION_QUESTION")), "").strip()
        email_client = latest_entry.get(str(getenv("EMAIL_QUESTION")), "") or ""
        safe_email = email_client.replace(".", "_") if email_client else "unknown"

        if not confession:
            return {
                "message": "Confession content is empty",
                "success": False,
                "data": [],
            }, 404

        print("\n==================================================", flush=True)
        print("📌 [BƯỚC 1/4] Kéo dữ liệu mới nhất từ Google Sheet...", flush=True)
        res = _save_confession(db.confession_data, confession, safe_email)
        print(f"➜ Kết quả lưu MongoDB: {res.get('message')}", flush=True)
        
        # Auto trigger AI Censorship & Auto Post to Facebook Page
        try:
            print("🤖 [BƯỚC 2/4] Đang gửi nội dung sang AI Gemini để kiểm duyệt...", flush=True)
            from src.services.moderator import _get_check_confession
            from src.services.post_facebook import post_fanpage
            ai_res = _get_check_confession()
            print(f"➜ AI Duyệt xong: {ai_res}", flush=True)

            print("🚀 [BƯỚC 3/4] Đang gửi bài viết sang Facebook Graph API...", flush=True)
            fb_res = post_fanpage()
            print(f"➜ Kết quả Facebook API: {fb_res}", flush=True)
            print("==================================================\n", flush=True)
        except Exception as pipeline_err:
            print(f"❌ [LỖI PIPELINE]: {pipeline_err}", flush=True)
            logger.error("Error in auto post pipeline: %s", pipeline_err)

        if isinstance(res, tuple):
            return res
        return res, 200

    except gspread.exceptions.APIError as e:
        logger.error("Google Sheets API error: %s", e)
        return {
            "message": f"Google Sheets error: {str(e)}",
            "success": False,
            "data": [],
        }, 500
    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        print(f"❌ UNEXPECTED ERROR IN GET_DATA_SHEET:\n{tb_str}", flush=True)
        logger.exception("Unexpected error in get_data_sheet")
        return {
            "message": f"Internal Server Error: {str(e)}",
            "error_detail": tb_str,
            "success": False,
            "data": [],
        }, 500
