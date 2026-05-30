import gspread
from oauth2client.service_account import ServiceAccountCredentials
from src.utils.create_id import generate_confession_id
from src.extension.db import db
from datetime import datetime, timedelta
from src.utils.pares_json import parse_json


def get_data_sheet() -> dict:
    try:

        collection = db.confession_data

        ####
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "credentials.json", scope
        )
        client = gspread.authorize(creds)

        sheet = client.open("Confession_app").sheet1
        data = sheet.get_all_records()
        ###

        latest_entry = data[-1]  # Get last data in sheet

        confession = latest_entry.get("Confession của bạn là gì?", "") or ""
        email_client = latest_entry.get("Gmail liên hệ của bạn là gì?", None)

        safe_email = email_client.replace(".", "_") if email_client else "unknown"

        id_confession = generate_confession_id(confession)

        data_output = {
            "Confession": confession,
            "authors": [
                safe_email,
            ],
            "id": id_confession,
            "post_time": {safe_email: datetime.now()},
            "count": 0,
            "active": False
        }

        _id = collection.find_one({"id": id_confession}, {"post_time": 1, "_id": 0})

        if _id:
            post_times = _id.get("post_time", {})
            if post_times:
                lastest_time = max(post_times.values())
            if (datetime.now() - lastest_time) > timedelta(
                hours=24
            ):  # HACK: 2 email unknown, how to get post time in last gmail in database? - 'success': True
                collection.insert_one(data_output)
                return {
                    "message": "Successfully saved confession",
                    "success": True,
                    "data": parse_json(data_output),
                }

            collection.update_one(
                {"id": id_confession},
                {
                    "$inc": {"count": 1},
                    "$addToSet": {"authors": email_client},
                    "$set": {f"post_time.{email_client}": datetime.now()},
                },
            )
            return {
                "message": "Successfully saved count confession",
                "success": True,
                "data": parse_json(data_output),
            }

        collection.insert_one(data_output)
        return {
            'message"': "Done to save data",
            "data": parse_json(data_output),
            "success": True,
        }

    except Exception as e:
        return {"message": str(e), "success": False, "data": []}
