from os import getenv
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)

print(str(getenv("CONFESSION_QUESTION")), str(getenv("EMAIL_QUESTION")))
