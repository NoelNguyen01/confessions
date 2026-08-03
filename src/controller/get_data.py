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

        res = _save_confession(db.confession_data, confession, safe_email)
        
        # Auto trigger AI Censorship & Auto Post to Facebook Page
        try:
            from src.services.moderator import _get_check_confession
            from src.services.post_facebook import post_fanpage
            _get_check_confession()
            post_fanpage()
        except Exception as pipeline_err:
            logger.error("Error in auto post pipeline: %s", pipeline_err)

        return res, 200

    except gspread.exceptions.APIError as e:
        logger.error("Google Sheets API error: %s", e)
        return {
            "message": f"Google Sheets error: {str(e)}",
            "success": False,
            "data": [],
        }, 500
    except Exception as e:
        logger.exception("Unexpected error in get_data_sheet")
        return {
            "message": f"Internal Server Error: {str(e)}",
            "success": False,
            "data": [],
        }, 500
