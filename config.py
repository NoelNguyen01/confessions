from dotenv import load_dotenv, find_dotenv
from os import getenv

load_dotenv(find_dotenv(), override=True)


class Config:
    api_key = getenv("GOOGLE_AI_API_KEY")
    AI_MODEL_NAME = getenv(
        "AI_MODEL_NAME", "gemini-2.0-flash"
    )  # model mặc định: gemini-2.0-flash (miễn phí)
    REPOST_COOLDOWN_HOURS = 24
