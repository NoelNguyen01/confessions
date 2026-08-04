import requests
from os import getenv
from src.extension.db import db
from src.utils.logger import logger
from src.utils.parse_json import parse_json
from datetime import datetime, timezone, timedelta

CONFESSION_LIMIT = 50
SEPARATOR = "─" * 20


def _build_message(confessions: list) -> str:
    """Gom các confession thành một chuỗi duy nhất để đăng."""
    lines = ["DANH SÁCH CONFESSION MỚI NHẤT\n"]
    for confession in confessions:
        content = confession.get("Confession", "")
        cfs_count = confession.get("cfs")
        lines.append(f"#cfs{cfs_count}: {content}\n{SEPARATOR}")

    message = "\n".join(lines)

    if len(message) > 60_000:
        logger.warning("Message too long (%d chars), truncating", len(message))
        message = message[:60_000] + "\n...(còn tiếp)"

    return message


def _mark_confessions(collection, confession_ids: list, active: bool) -> None:
    """Cập nhật trạng thái active cho danh sách confession."""
    collection.update_many(
        {"_id": {"$in": confession_ids}}, {"$set": {"active": active}}
    )


def _acquire_lock(lock_collection) -> bool:
    """
    Distributed lock dùng MongoDB atomic findOneAndUpdate.
    TTL 5 phút để tránh deadlock khi process chết giữa chừng.
    """
    now = datetime.now(timezone.utc)
    five_minutes_ago = now - timedelta(minutes=5)

    result = lock_collection.find_one_and_update(
        {
            "lock_name": "post_fanpage",
            "$or": [
                {"locked": False},
                {"locked_at": {"$lt": five_minutes_ago}},
            ],
        },
        {"$set": {"locked": True, "locked_at": now}},
        upsert=True,
        return_document=True,
    )
    return result is not None


def _release_lock(lock_collection) -> None:
    lock_collection.update_one(
        {"lock_name": "post_fanpage"},
        {"$set": {"locked": False}},
    )


def post_fanpage() -> dict:
    """
    Chế độ đăng duy nhất: Sử dụng Webhook (n8n / Make.com / Pipedream / Custom Webhook).
    Không dùng Facebook Token.
    """
    lock_collection = db.post_locks
    collection_confession = db.confession_data
    confession_ids = []

    # ── 1. Lấy lock, tránh nhiều process chạy đồng thời ──
    if not _acquire_lock(lock_collection):
        logger.info("post_fanpage: another process is running, skipping")
        return {"message": "Already running", "success": False}

    try:
        # ── 2. Lấy tối đa 50 confession chưa xử lý (active: False) ──
        list_confession = list(
            collection_confession.find({"active": False})
            .sort("cfs", 1)
            .limit(CONFESSION_LIMIT)
        )

        if not list_confession:
            return {"message": "No data to post", "success": False}

        confession_ids = [c["_id"] for c in list_confession]

        # ── 3. Đánh dấu "đang xử lý" ──
        _mark_confessions(collection_confession, confession_ids, active=True)

        # ── 4. Lấy URL Webhook từ file .env ──
        webhook_url = str(getenv("FB_WEBHOOK_URL", "")).strip().strip('"').strip("'")

        if not webhook_url:
            print("   ⚠️ LỖI: Bạn chưa cấu hình FB_WEBHOOK_URL trong file .env!", flush=True)
            _mark_confessions(collection_confession, confession_ids, active=False)
            return {
                "message": "Chưa cấu hình FB_WEBHOOK_URL trong file .env!",
                "success": False
            }

        print(f"   🚀 Đang gửi bài qua Webhook Tự Động: {webhook_url[:40]}...", flush=True)
        message_text = _build_message(list_confession)
        clean_confessions = parse_json(list_confession)

        payload = {
            "message": message_text,
            "confessions": clean_confessions
        }

        try:
            res = requests.post(webhook_url, json=payload, timeout=30)
            print(f"   Webhook response: status={res.status_code}, content={res.text[:150]}", flush=True)

            if res.status_code in (200, 201, 202, 204):
                logger.info("post_fanpage: posted via webhook successfully")
                print("   🎉 Gửi Webhook thành công! Đã chuyển payload đến Webhook.", flush=True)
                return {"message": "Posted successfully via webhook", "success": True}
            else:
                print(f"   ❌ Webhook trả về status code lỗi ({res.status_code})", flush=True)
                _mark_confessions(collection_confession, confession_ids, active=False)
                return {"message": f"Webhook returned HTTP {res.status_code}", "success": False}

        except Exception as w_err:
            print(f"   ❌ LỖI kết nối Webhook: [{type(w_err).__name__}] {w_err}", flush=True)
            _mark_confessions(collection_confession, confession_ids, active=False)
            return {"message": f"Webhook error: {w_err}", "success": False}

    except requests.exceptions.Timeout:
        logger.error("post_fanpage: request timed out")
        if confession_ids:
            _mark_confessions(collection_confession, confession_ids, active=False)
        return {"message": "Request timed out", "success": False}

    except Exception as e:
        logger.exception("post_fanpage: unexpected error")
        if confession_ids:
            _mark_confessions(collection_confession, confession_ids, active=False)
        return {"message": f"Internal Server Error: {str(e)}", "success": False}

    finally:
        _release_lock(lock_collection)
