"""
Tool xử lý dữ liệu confession kẹt trong MongoDB.

Các bài cũ bị đánh dấu active=True sẽ bị hệ thống BỎ QUA (không duyệt, không đăng lại).
Tool này giúp:
  --list        : liệt kê các bài đang kẹt (mặc định, an toàn, không đổi dữ liệu)
  --reprocess   : set active=False + xoá cờ censored/status/data_ai_result để hệ thống xử lý lại
  --delete      : XOÁ VĨNH VIỄN các bài được chọn (không thể khôi phục)

Chạy:
  .venv\\Scripts\\python.exe script\\reset_db.py --list
  .venv\\Scripts\\python.exe script\\reset_db.py --reprocess
  .venv\\Scripts\\python.exe script\\reset_db.py --delete
"""
import sys
import os
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)

import certifi
from pymongo import MongoClient


def _safe(text):
    return str(text).encode("ascii", "replace").decode("ascii")


def main():
    uri = os.getenv("MONGO_URI", "")
    if not uri:
        print("MONGO_URI chưa được cấu hình trong .env")
        sys.exit(1)

    client = MongoClient(uri, serverSelectionTimeoutMS=8000, tlsCAFile=certifi.where())
    db = client["Confession"]
    col = db.confession_data

    total = col.count_documents({})
    active_true = col.count_documents({"active": True})
    print(f"confession_data: total={total}, active=True={active_true}")

    docs = list(col.find({}, {"_id": 1, "id": 1, "cfs": 1, "Confession": 1, "active": 1}))

    if not docs:
        print("Không có dữ liệu nào trong collection.")
        client.close()
        return

    for d in docs:
        print(
            f"  cfs={d.get('cfs')} active={d.get('active')} "
            f"confession={_safe((d.get('Confession') or '')[:60])}"
        )

    mode = None
    if "--delete" in sys.argv:
        mode = "delete"
    elif "--reprocess" in sys.argv:
        mode = "reprocess"

    if not mode:
        print("\nMặc định chỉ hiển thị. Dùng --reprocess hoặc --delete để thay đổi dữ liệu.")
        client.close()
        return

    target_ids = [d["_id"] for d in docs]

    if mode == "delete":
        res = col.delete_many({"_id": {"$in": target_ids}})
        print(f"\nĐã xoá {res.deleted_count} bài. KHÔNG THỂ KHÔI PHỤC.")
    elif mode == "reprocess":
        res = col.update_many(
            {"_id": {"$in": target_ids}},
            {
                "$set": {"active": False},
                "$unset": {"censored": "", "status": "", "data_ai_result": ""},
            },
        )
        print(
            f"\nĐã đặt active=False cho {res.modified_count} bài. "
            "Hệ thống sẽ duyệt + đăng lại trong lần /submit hoặc /check tiếp theo."
        )

    client.close()


if __name__ == "__main__":
    main()
