from pymongo import ReturnDocument
from src.extension.db import db


def get_next_cfs_number() -> int:
    counters_col = db.counters

    counter = counters_col.find_one_and_update(
        {"_id": "cfs_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    return counter["seq"]
