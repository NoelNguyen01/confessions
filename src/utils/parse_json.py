from datetime import datetime, date

def parse_json(data):
    """
    Recursively parse BSON / MongoDB objects (ObjectId, datetime, date, etc.)
    into JSON-serializable Python data structures.
    """
    if isinstance(data, list):
        return [parse_json(i) for i in data]
    elif isinstance(data, dict):
        res = {}
        for k, v in data.items():
            if k == "_id" or type(v).__name__ == "ObjectId":
                res[k] = str(v)
            else:
                res[k] = parse_json(v)
        return res
    elif type(data).__name__ == "ObjectId":
        return str(data)
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    return data

