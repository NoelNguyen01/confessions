from google.genai.errors import APIError
from config import Config
from src.extension.google_ai import client
from src.utils.extract_json import extract_json
from src.prompt.moderation import _return_prompt_from_list_cfs
from src.extension.db import db
from datetime import datetime


def chat_main_ai(ai_model: str, content_input: str, confession_input: str = "") -> str:
    try:
        response = client.models.generate_content(
            model=ai_model,
            contents=content_input + confession_input,
        )
        return (
            response.text
            if response and response.text
            else "No response received from AI"
        )
    except APIError as e:
        print(e, flush=True)  # TODO: Implement API conversion
    except Exception as e:
        print(e, flush=True)


def _get_check_confession():
    try:

        collection = db.confession_data

        _id = collection.find(
            {"active": False}, {"Confession": 1, "_id": 0, "status": 1, "id": 1}
        )

        if not _id:
            return {
                "success": False,
                "message": "An error occurred while retrieving the data",
            }

        _list = {}

        for user in _id:
            status = user.get("status", None)

            if not status:
                _list[user.get("Confession")] = user.get("id")

        _message = _return_prompt_from_list_cfs(**_list)

        _result_ai = chat_main_ai(
            ai_model=Config.AI_MODEL_NAME,
            confession_input=str(_message),
            content_input="",
        )

        json_data = extract_json(_result_ai)

        for _result in json_data:

            _id_find = _result.get("id_origin")
            _result.pop("id_origin", None)
            _result["check_time"] = datetime.now()

            collection.update_one(
                {"id": _id_find},
                {
                    "$set": {
                        "data_ai_result": _result,
                        "active": True,
                    }
                },
            )

        return {"success": True, "message": "Successful censorship", "data": json_data}
    except Exception as e:
        print(e, flush=True)
