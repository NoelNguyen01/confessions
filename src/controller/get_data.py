from src.services.get_data import get_data_sheet


def submit_confession():

    result = get_data_sheet()

    if not result["success"]:
        print(result["message"], flush=True)
        return {"error": result["data"], "message": result["message"]}, 500

    return {"message": "Thành công", "data": result["data"]}, 200
