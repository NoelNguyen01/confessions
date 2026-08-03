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
        env_page_id = str(getenv("PAGE_ID", "")).strip().strip('"').strip("'")
        user_token = str(getenv("ACCESS_TOKEN", "")).strip().strip('"').strip("'")

        if not env_page_id or not user_token:
            raise EnvironmentError("PAGE_ID hoặc ACCESS_TOKEN chưa được cấu hình")

        print(f"   🔍 Check Access Token: Độ dài={len(user_token)}, Tiền tố='{user_token[:15]}...'", flush=True)
        if not user_token.startswith("EAA"):
            print(f"   ⚠️ CẢNH BÁO: ACCESS_TOKEN có vẻ SAI LOẠI! Token Graph API chuẩn phải bắt đầu bằng 'EAA...'", flush=True)

        # Danh sách Page ID thử nghiệm (bao gồm PAGE_ID từ env và Real Delegate Page ID: 1327276117125256)
        candidate_page_ids = [env_page_id, "1327276117125256"]
        seen = set()
        candidate_page_ids = [p for p in candidate_page_ids if p and not (p in seen or seen.add(p))]

        page_token = user_token

        # Thử lấy Page Token qua /me/accounts (nếu ACCESS_TOKEN là User Token)
        try:
            acc_url = f"https://graph.facebook.com/me/accounts"
            acc_resp = requests.get(acc_url, params={"access_token": user_token}, timeout=10)
            acc_data = acc_resp.json()
            if "data" in acc_data and isinstance(acc_data["data"], list):
                for page in acc_data["data"]:
                    p_id = str(page.get("id"))
                    if p_id in candidate_page_ids:
                        page_token = page.get("access_token", user_token)
                        print(f"   ✅ Lấy thành công Page Token mới cho Page ID {p_id}!", flush=True)
                        break
        except Exception as t_err:
            print(f"   ⚠️ Token exchange info: {t_err}", flush=True)

        # Danh sách endpoint thử nghiệm (/me/feed là chuẩn nhất khi dùng Page Token)
        candidate_endpoints = [
            f"https://graph.facebook.com/v22.0/me/feed",
            f"https://graph.facebook.com/v22.0/{env_page_id}/feed",
            f"https://graph.facebook.com/v22.0/1327276117125256/feed"
        ]

        last_res = None
        for endpoint_url in candidate_endpoints:
            print(f"   🚀 Thử đăng bài lên Facebook Endpoint: {endpoint_url}...", flush=True)
            payload = {
                "message": _build_message(list_confession),
                "access_token": page_token,
            }

            response = requests.post(endpoint_url, data=payload, timeout=30)
            res_data = response.json()
            print(f"   Facebook API response: status={response.status_code}, data={res_data}", flush=True)

            if response.status_code == 200 and "id" in res_data:
                logger.info("post_fanpage: posted %d confessions to %s", len(list_confession), endpoint_url)
                return {"message": "Posted successfully", "success": True, "data": res_data}
            last_res = res_data

        # Facebook lỗi → rollback
        logger.error("post_fanpage: Facebook error %s", last_res)
        _mark_confessions(collection_confession, confession_ids, active=False)
        return {"message": f"Facebook API error: {last_res.get('error', {}).get('message', last_res) if isinstance(last_res, dict) else last_res}", "success": False, "data": last_res}

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
