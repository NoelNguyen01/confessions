from dotenv import load_dotenv, find_dotenv
from os import getenv

load_dotenv(find_dotenv(), override=True)


class Config:
    api_key = getenv("GOOGLE_AI_API_KEY")
    groq_api_key = getenv("GROQ_API_KEY")
    AI_MODEL_NAME = getenv(
        "AI_MODEL_NAME", "gemini-3.5-flash-lite"
    )  # Model mặc định: gemini-3.5-flash-lite (tốc độ cao, rào cản limit thấp)
    REPOST_COOLDOWN_HOURS = 24

