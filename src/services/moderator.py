from google import genai
from google.genai.errors import APIError
from config import Config


def moderator_services():

    client = genai.Client(api_key=Config.api_key)

    try:
        response = client.models.generate_content(
            model=Config.AI_MODEL_NAME,
            contents=Config.AI_MODERATION_PROMPT,
        )
    except APIError as e:
        print(e, flush=True)
    except Exception as e:
        print(e, flush=True)

    return response.text


print(moderator_services())
