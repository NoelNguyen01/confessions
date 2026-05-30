import requests
from os import getenv
from src.extension.db import db
from src.utils.logger import logger

def post_fanpage(): #TODO: perform the time checking function
    try:
        collection_confession = db.confession_data

        cursor_data = collection_confession.find({"active": False})
        list_confession = list(cursor_data)

        if len(list_confession) == 0:
            return {"message": "no data to post", "success": False}

        page_id = str(getenv("PAGE_ID"))
        page_token = str(getenv("ACCESS_TOKEN"))
        url = f"https://graph.facebook.com/v25.0/{page_id}/feed"

        chuoi_tin_nhan_tong = "DANH SÁCH CONFESSION MỚI NHẤT\n\n"

        for confession in list_confession:
            content = confession.get("Confession")
            _cfs_count = confession.get("cfs")
            doan_van_ban = f"#cfs{_cfs_count}: {content}\n"
            chuoi_tin_nhan_tong += doan_van_ban + "--------------------\n"

        payload = {"message": chuoi_tin_nhan_tong, "access_token": page_token}

        response = requests.post(url, data=payload, timeout=30)
        res_data = response.json()

        if response.status_code == 200 and "id" in res_data:
            for confession in list_confession:
                _id = confession.get("id")
                collection_confession.update_one(
                    {"id": _id}, {"$set": {"active": True}}
                )
            return {"message": "Posted successfully", "success": True, "data": res_data}
        return {
            "message": "There was an error on Facebooks part",
            "success": False,
            "data": res_data,
        }
    except requests.exceptions.Timeout:
        return {"message": "Request to Facebook timed out", "success": False}
    except Exception as e:
        return {"message": f"Internal Server Error: {str(e)}", "success": False}
