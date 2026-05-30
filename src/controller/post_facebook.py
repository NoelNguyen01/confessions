from src.services.post_facebook import post_fanpage
from utils.logger import logger

def post_facebook():
    result = post_fanpage()

    if result["success"]:
        return {"message": "Successfully posted", "success": True}, 200
    logger.error(result['data'])
    return {"message": "There was an error on the server side", "success": False}, 500
