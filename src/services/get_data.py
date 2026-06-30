import gspread
from oauth2client.service_account import ServiceAccountCredentials
from src.utils.create_id import generate_confession_id
from src.utils.pares_json import parse_json
from src.utils.upset_count import get_next_cfs_number
from datetime import datetime, timedelta, timezone
from os import getenv
from functools import lru_cache
from src.utils.logger import logger
from config import Config


@lru_cache(maxsize=1)
def _get_sheet_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds)


def _get_sheet():
    try:
        client = _get_sheet_client()
        return client.open(str(getenv("SHEET_NAME"))).sheet1
    except gspread.exceptions.APIError:
        _get_sheet_client.cache_clear()
        client = _get_sheet_client()
        return client.open(str(getenv("SHEET_NAME"))).sheet1


def _fetch_latest_entry(sheet) -> dict | None:
    col_a = sheet.col_values(1)
    last_index = len(col_a)

    if last_index < 2:
        logger.info("Sheet has no data outside of the header")
        return None

    header = [h.strip() for h in sheet.row_values(1)]
    last_row = sheet.row_values(last_index)
    last_row += [""] * (len(header) - len(last_row))

    return dict(zip(header, [v.strip() for v in last_row]))


def _build_confession_doc(confession: str, safe_email: str) -> dict:
    return {
        "Confession": confession,
        "authors": [safe_email],
        "id": generate_confession_id(confession),
        "post_time": {safe_email: datetime.now(timezone.utc)},
        "count": 0,
        "active": False,
    }


def _save_confession(collection, confession: str, safe_email: str) -> dict:
    now = datetime.now(timezone.utc)
    doc = _build_confession_doc(confession, safe_email)
    confession_id = doc["id"]

    existing = collection.find_one(
        {"id": confession_id}, {"post_time": 1, "authors": 1, "_id": 0}
    )

    if not existing:
        doc["cfs"] = get_next_cfs_number()
        collection.insert_one(doc)
        logger.info("New confession inserted: %s", confession_id)
        return {
            "message": "Successfully saved confession",
            "success": True,
            "data": parse_json(doc),
        }

    post_times: dict = existing.get("post_time", {})
    last_time_by_email = post_times.get(safe_email)

    if last_time_by_email:
        if last_time_by_email.tzinfo is None:
            last_time_by_email = last_time_by_email.replace(tzinfo=timezone.utc)

        if (now - last_time_by_email) < timedelta(hours=Config.REPOST_COOLDOWN_HOURS):
            logger.info("Duplicate submission from %s within cooldown", safe_email)
            return {
                "message": "You already submitted this confession recently",
                "success": False,
                "data": [],
            }

    collection.update_one(
        {"id": confession_id},
        {
            "$inc": {"count": 1},
            "$addToSet": {"authors": safe_email},
            "$set": {f"post_time.{safe_email}": now},
        },
    )
    logger.info("Confession count updated: %s by %s", confession_id, safe_email)
    return {
        "message": "Successfully updated confession count",
        "success": True,
        "data": parse_json(doc),
    }
