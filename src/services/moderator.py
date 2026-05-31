from google import genai
from google.genai.errors import APIError
from os import getenv
from dotenv import find_dotenv, load_dotenv
from config import Config

load_dotenv(find_dotenv(), override=True)

def moderator_services():
    
    client = genai.Client(api_key=Config.api_key)

    try:
        response = client.models.generate_content(
            model=Config.AI_MODEL_NAME,
            contents="giới thiệu 1 chút về bạn đi",
        )
    except APIError as e:
        print(e, flush=True)
    except Exception as e:
        print(e, flush=True)

    return response.text

print(moderator_services())