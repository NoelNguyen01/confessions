import traceback
import gspread
from src.services.get_data import _get_sheet, _fetch_latest_entry, _save_confession
from src.utils.logger import logger
from os import getenv
from src.extension.db import db


def get_data_sheet() -> dict:
    try:
        # ── BƯỚC 1: Kéo dữ liệu từ Google Sheet ──
        print("\n" + "=" * 50, flush=True)
        print("📌 [BƯỚC 1/4] Kéo dữ liệu từ Google Sheet...", flush=True)

        try:
            sheet = _get_sheet()
        except Exception as e:
            print(f"❌ [LỖI BƯỚC 1] Không thể mở Google Sheet: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            return {"message": f"Lỗi kết nối Google Sheet: {type(e).__name__}: {e}", "success": False, "data": []}, 500

        try:
            latest_entry = _fetch_latest_entry(sheet)
        except Exception as e:
            print(f"❌ [LỖI BƯỚC 1] Không thể đọc dữ liệu Sheet: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            return {"message": f"Lỗi đọc Sheet: {type(e).__name__}: {e}", "success": False, "data": []}, 500

        if not latest_entry:
            print("⚠️ Sheet trống, không có dữ liệu", flush=True)
            return {"message": "Sheet has no data", "success": False, "data": []}, 404

        confession_q = str(getenv("CONFESSION_QUESTION", ""))
        email_q = str(getenv("EMAIL_QUESTION", ""))
        print(f"   CONFESSION_QUESTION = '{confession_q}'", flush=True)
        print(f"   EMAIL_QUESTION = '{email_q}'", flush=True)
        print(f"   Sheet headers = {list(latest_entry.keys())}", flush=True)

        confession = latest_entry.get(confession_q, "").strip()
        email_client = latest_entry.get(email_q, "") or ""
        safe_email = email_client.replace(".", "_") if email_client else "unknown"

        if not confession:
            print("⚠️ Nội dung confession trống!", flush=True)
            return {"message": "Confession content is empty", "success": False, "data": []}, 404

        print(f"✅ Confession: '{confession[:80]}...'", flush=True)

        # ── BƯỚC 2: Lưu vào MongoDB ──
        print("📌 [BƯỚC 2/4] Lưu confession vào MongoDB...", flush=True)
        try:
            res = _save_confession(db.confession_data, confession, safe_email)
            print(f"✅ MongoDB: {res.get('message', 'OK')}", flush=True)
        except Exception as e:
            print(f"❌ [LỖI BƯỚC 2] Lỗi MongoDB: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            return {"message": f"Lỗi MongoDB: {type(e).__name__}: {e}", "success": False, "data": []}, 500

        # ── BƯỚC 3: AI Gemini kiểm duyệt ──
        print("📌 [BƯỚC 3/4] AI Gemini kiểm duyệt nội dung...", flush=True)
        try:
            from src.services.moderator import _get_check_confession
            ai_res = _get_check_confession()
            print(f"✅ AI: {ai_res}", flush=True)
        except Exception as e:
            print(f"⚠️ [LỖI BƯỚC 3] AI kiểm duyệt lỗi (bỏ qua, vẫn tiếp tục): {e}", flush=True)
            print(traceback.format_exc(), flush=True)

        # ── BƯỚC 4: Đăng bài lên Facebook ──
        print("📌 [BƯỚC 4/4] Đăng bài lên Facebook...", flush=True)
        try:
            from src.services.post_facebook import post_fanpage
            fb_res = post_fanpage()
            print(f"✅ Facebook: {fb_res}", flush=True)
        except Exception as e:
            print(f"⚠️ [LỖI BƯỚC 4] Đăng Facebook lỗi: {e}", flush=True)
            print(traceback.format_exc(), flush=True)

        print("=" * 50 + "\n", flush=True)

        # Trả về kết quả cho Apps Script
        return {"message": "Pipeline completed", "success": True, "data": []}, 200

    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"❌ UNEXPECTED ERROR:\n{tb_str}", flush=True)
        logger.exception("Unexpected error in get_data_sheet")
        return {"message": f"Internal Server Error: {type(e).__name__}: {e}", "success": False, "data": []}, 500
