from google import genai
from config import Config

client = genai.Client(api_key=Config.api_key)
