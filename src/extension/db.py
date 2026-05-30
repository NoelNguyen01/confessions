from database import get_db

db = get_db()

if db is None:
    raise Exception("Failed to initialize database connection")
