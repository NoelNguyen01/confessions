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


def _resolve_page_token(user_token: str, env_page_id: str) -> tuple[str, str]:
    """
    Kiểm tra và tự động chuyển đổi User Access Token thành Page Access Token.
    Trả về tuple (page_access_token, effective_page_id).
    """
    print(f"   🔍 Check Access Token: Độ dài={len(user_token)}, Tiền tố='{user_token[:15]}...'", flush=True)

    # 1. Gọi /me để kiểm tra token hiện tại là User hay Page Token
    try:
        me_url = "https://graph.facebook.com/v22.0/me"
        me_resp = requests.get(me_url, params={"access_token": user_token}, timeout=10)
        me_data = me_resp.json()

        if me_resp.status_code == 200 and "id" in me_data:
            me_id = str(me_data["id"])
            me_name = me_data.get("name", "")

            # Nếu /me trả về có category hoặc ID khớp với PAGE_ID -> Token đã là Page Token!
            if "category" in me_data or (env_page_id and me_id == env_page_id):
                print(f"   ✅ Access Token hiện tại ALREADY là Page Access Token cho Page: '{me_name}' (ID: {me_id})", flush=True)
                return user_token, me_id

            print(f"   ℹ️ Access Token là User Token của user: '{me_name}' (ID: {me_id}). Đang đổi sang Page Access Token...", flush=True)
        else:
            print(f"   ⚠️ GET /me response: status={me_resp.status_code}, data={me_data}", flush=True)

    except Exception as e:
        print(f"   ⚠️ Không thể inspect /me: {e}", flush=True)

    # 2. Thử lấy Page Token từ /me/accounts (Dành cho User Access Token)
    try:
        acc_url = "https://graph.facebook.com/v22.0/me/accounts"
        acc_resp = requests.get(acc_url, params={"access_token": user_token}, timeout=10)
        acc_data = acc_resp.json()

        if acc_resp.status_code == 200 and "data" in acc_data and isinstance(acc_data["data"], list):
            pages = acc_data["data"]
            print(f"   🔎 Tìm thấy {len(pages)} Page(s) quản lý bởi User Token.", flush=True)

            # Ưu tiên khớp với env_page_id
            for page in pages:
                p_id = str(page.get("id", ""))
                p_token = page.get("access_token", "")
                p_name = page.get("name", "")
                if env_page_id and p_id == env_page_id:
                    print(f"   ✅ Lấy thành công Page Access Token cho Page '{p_name}' (ID: {p_id}) từ /me/accounts!", flush=True)
                    return p_token, p_id

            # Nếu không khớp ID cụ thể, lấy Page đầu tiên có token
            if pages and "access_token" in pages[0]:
                p_id = str(pages[0].get("id", ""))
                p_token = pages[0].get("access_token", "")
                p_name = pages[0].get("name", "")
                print(f"   ✅ Lấy Page Access Token của Page đầu tiên '{p_name}' (ID: {p_id})!", flush=True)
                return p_token, p_id
        else:
            err_msg = acc_data.get("error", {}).get("message", acc_data)
            print(f"   ⚠️ Gọi /me/accounts thất bại: {err_msg}", flush=True)

    except Exception as e:
        print(f"   ⚠️ Lỗi lấy /me/accounts: {e}", flush=True)

    # 3. Thử trực tiếp /{page_id}?fields=access_token nếu có PAGE_ID
    if env_page_id:
        try:
            p_url = f"https://graph.facebook.com/v22.0/{env_page_id}"
            p_resp = requests.get(p_url, params={"fields": "access_token", "access_token": user_token}, timeout=10)
            p_data = p_resp.json()
            if p_resp.status_code == 200 and "access_token" in p_data:
                print(f"   ✅ Lấy thành công Page Access Token từ /{env_page_id}?fields=access_token!", flush=True)
                return p_data["access_token"], env_page_id
            else:
                err_msg = p_data.get("error", {}).get("message", p_data)
                print(f"   ⚠️ Gọi /{env_page_id}?fields=access_token thất bại: {err_msg}", flush=True)
        except Exception as e:
            print(f"   ⚠️ Lỗi lấy Page Token trực tiếp từ Page ID {env_page_id}: {e}", flush=True)

    # 4. Fallback: Dùng trực tiếp user_token
    print("   ⚠️ Không thể đổi sang Page Token riêng, fallback dùng nguyên Access Token ban đầu.", flush=True)
    return user_token, env_page_id


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

        # ── 4. Xử lý Webhook (Nếu được cấu hình) ──
        webhook_url = str(getenv("FB_WEBHOOK_URL", "")).strip().strip('"').strip("'")
        env_page_id = str(getenv("PAGE_ID", "")).strip().strip('"').strip("'")
        raw_token = str(getenv("ACCESS_TOKEN", "")).strip().strip('"').strip("'")

        if webhook_url:
            print(f"   🚀 Đang gửi bài qua Webhook Tự Động: {webhook_url[:30]}...", flush=True)
            message_text = _build_message(list_confession)
            try:
                # Sử dụng parse_json an toàn xử lý ObjectId và datetime
                clean_confessions = parse_json(list_confession)
                payload = {"message": message_text, "confessions": clean_confessions}
                res = requests.post(webhook_url, json=payload, timeout=30)
                print(f"   Webhook response: status={res.status_code}, content={res.text[:150]}", flush=True)
                if res.status_code in (200, 201, 204):
                    logger.info("post_fanpage: posted via webhook successfully")
                    return {"message": "Posted successfully via webhook", "success": True}
            except Exception as w_err:
                print(f"   ❌ LỖI Webhook: [{type(w_err).__name__}] {w_err}", flush=True)

        if not raw_token:
            raise EnvironmentError("ACCESS_TOKEN chưa được cấu hình trong biến môi trường (.env)")

        # ── 5. Resolve Page Access Token & Page ID ──
        page_token, page_id = _resolve_page_token(raw_token, env_page_id)

        # ── 6. Đăng bài lên Facebook Graph API ──
        # Danh sách Endpoint hợp lệ để thử đăng
        candidate_endpoints = []
        if page_id:
            candidate_endpoints.append(f"https://graph.facebook.com/v22.0/{page_id}/feed")
        candidate_endpoints.append("https://graph.facebook.com/v22.0/me/feed")

        # Loại bỏ endpoint trùng
        seen_ep = set()
        candidate_endpoints = [e for e in candidate_endpoints if e and not (e in seen_ep or seen_ep.add(e))]

        last_res = None
        message_text = _build_message(list_confession)

        for endpoint_url in candidate_endpoints:
            print(f"   🚀 Thử đăng bài lên Facebook Endpoint: {endpoint_url}...", flush=True)

            # Standard Form-urlencoded payload for Facebook Graph API
            payload = {
                "message": message_text,
                "access_token": page_token
            }
            # Bỏ các value None / empty
            payload = {k: v for k, v in payload.items() if v is not None and v != ""}

            try:
                response = requests.post(endpoint_url, data=payload, timeout=30)
                try:
                    res_data = response.json()
                except Exception:
                    res_data = {"raw_text": response.text}

                print(f"   Facebook API response: status={response.status_code}, data={res_data}", flush=True)

                if response.status_code == 200 and "id" in res_data:
                    logger.info("post_fanpage: posted %d confessions to %s", len(list_confession), endpoint_url)
                    print(f"   🎉 Đăng bài thành công! Post ID: {res_data.get('id')}", flush=True)
                    return {"message": "Posted successfully", "success": True, "data": res_data}

                last_res = res_data

                # Debug chi tiết khi gặp lỗi
                if isinstance(res_data, dict) and "error" in res_data:
                    err_info = res_data["error"]
                    err_code = err_info.get("code")
                    err_msg = err_info.get("message")
                    err_type = err_info.get("type")
                    err_sub = err_info.get("error_subcode")
                    fbtrace = err_info.get("fbtrace_id")
                    print(f"   ❌ Facebook Error: Code={err_code}, Subcode={err_sub}, Type={err_type}, Message={err_msg}, fbtrace_id={fbtrace}", flush=True)

                    if err_code in (1, 100, 190, 200):
                        print("   💡 [HƯỚNG DẪN FIX FACEBOOK GRAPH API LỖI]:", flush=True)
                        print("      - Token sử dụng phải là PAGE ACCESS TOKEN (không phải User Token đơn thuần).", flush=True)
                        print("      - Facebook App cần các quyền (Permissions): `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`.", flush=True)
                        print("      - Nếu token hết hạn, hãy làm mới (Refresh Token) hoặc tạo Long-Lived Page Access Token.", flush=True)

            except Exception as req_err:
                print(f"   ⚠️ Lỗi kết nối endpoint {endpoint_url}: [{type(req_err).__name__}] {req_err}", flush=True)

        # Facebook lỗi → rollback active = False
        logger.error("post_fanpage: Facebook error %s", last_res)
        _mark_confessions(collection_confession, confession_ids, active=False)
        return {
            "message": f"Facebook API error: {last_res.get('error', {}).get('message', last_res) if isinstance(last_res, dict) else last_res}",
            "success": False,
            "data": last_res
        }

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
        # ── 7. Luôn giải phóng lock dù thành công hay thất bại ──
        _release_lock(lock_collection)

