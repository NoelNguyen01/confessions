import requests
from os import getenv
from src.extension.db import db
from src.utils.logger import logger
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
    Trả về True nếu lấy được lock, False nếu đang bị giữ.
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
    lock_collection = db.post_locks
    collection_confession = db.confession_data
    confession_ids = []

    # ── 1. Lấy lock, tránh nhiều process chạy đồng thời ──
    if not _acquire_lock(lock_collection):
        logger.info("post_fanpage: another process is running, skipping")
        return {"message": "Already running", "success": False}

    try:
        # ── 2. Lấy tối đa 50 confession, sắp xếp theo thứ tự ──
        list_confession = list(
            collection_confession.find({"active": False})
            .sort("cfs", 1)
            .limit(CONFESSION_LIMIT)
        )

        if not list_confession:
            return {"message": "No data to post", "success": False}

        confession_ids = [c["_id"] for c in list_confession]

        # ── 3. Đánh dấu "đang xử lý" trước khi gọi API ──
        _mark_confessions(collection_confession, confession_ids, active=True)

        # ── 4. Gọi Facebook API ──
        page_id = getenv("PAGE_ID")
        user_token = getenv("ACCESS_TOKEN")

        if not page_id or not user_token:
            raise EnvironmentError("PAGE_ID hoặc ACCESS_TOKEN chưa được cấu hình")

        # Tự động đổi User Token → Page Token
        print(f"   Đang lấy Page Access Token cho page {page_id}...", flush=True)
        accounts_url = f"https://graph.facebook.com/v22.0/me/accounts?access_token={user_token}"
        acc_resp = requests.get(accounts_url, timeout=15)
        acc_data = acc_resp.json()
        print(f"   /me/accounts response: {acc_data}", flush=True)

        page_token = user_token  # fallback
        if "data" in acc_data:
            for page in acc_data["data"]:
                if str(page.get("id")) == str(page_id):
                    page_token = page["access_token"]
                    print(f"   ✅ Đã lấy được Page Token!", flush=True)
                    break

        url = f"https://graph.facebook.com/v22.0/{page_id}/feed"
        payload = {
            "message": _build_message(list_confession),
            "access_token": page_token,
        }

        response = requests.post(url, data=payload, timeout=30)
        res_data = response.json()
        print(f"   Facebook response: {res_data}", flush=True)

        # ── 5. Xử lý kết quả ──
        if response.status_code == 200 and "id" in res_data:
            logger.info("post_fanpage: posted %d confessions", len(list_confession))
            return {"message": "Posted successfully", "success": True, "data": res_data}

        # Facebook lỗi → rollback
        logger.error("post_fanpage: Facebook error %s", res_data)
        _mark_confessions(collection_confession, confession_ids, active=False)
        return {"message": "Facebook API error", "success": False, "data": res_data}

    except EnvironmentError as e:
        logger.error("post_fanpage: config error — %s", e)
        return {"message": str(e), "success": False}

    except requests.exceptions.Timeout:
        logger.error("post_fanpage: request timed out")
        if confession_ids:
            _mark_confessions(collection_confession, confession_ids, active=False)
        return {"message": "Request to Facebook timed out", "success": False}

    except Exception as e:
        logger.exception("post_fanpage: unexpected error")
        if confession_ids:
            _mark_confessions(collection_confession, confession_ids, active=False)
        return {"message": f"Internal Server Error: {str(e)}", "success": False}

    finally:
        # ── 6. Luôn giải phóng lock dù thành công hay thất bại ──
        _release_lock(lock_collection)
