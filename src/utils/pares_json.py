def parse_json(data):
    if isinstance(data, list):
        return [parse_json(i) for i in data]
    if isinstance(data, dict):
        for k, v in data.items():
            if k == "_id" and not isinstance(v, str):
                data[k] = str(v)
            else:
                data[k] = parse_json(v)
    return data
