"""
This module provides functions to initialize and access a MongoDB database connection. It uses the `pymongo` library to manage the connection and ensures that the connection is established in a thread-safe manner. The MongoDB URI is expected to be set in the environment variable `MONGO_URI`. The module includes error handling to log any connection issues and raises exceptions if the connection fails.
@copyright: 2026 DropVault Team
@created: 2026-04-17 5:07 PM
@Author: CuSam
@license: Private / Internal Use Only
"""

from os import getenv
from threading import Lock
from pymongo import MongoClient
from pymongo.database import Database

_client = None
_db = None
_lock = Lock()


def init_db() -> Database:
    """
    Initializes the MongoDB connection and returns the database instance. This function is designed to be thread-safe, ensuring that only one connection is established even if multiple threads attempt to initialize the database simultaneously.
    Returns:
        Database: The MongoDB database instance.
    """
    global _client, _db

    with _lock:
        if _db is not None:
            return _db

        uri = getenv("MONGO_URI")
        if not uri:
            raise ValueError("MONGO_URI is not set")

        try:
            _client = MongoClient(
                uri,
                maxPoolSize=50,
                minPoolSize=5,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
            )

            _client.admin.command("ping")

            _db = _client["Confession"]
            print("MongoDB connected successfully", flush=True)

            return _db

        except Exception as e:
            print(f"MongoDB connection failed: {e}", flush=True)
            raise


def get_db() -> Database:
    """
    Returns the MongoDB database instance. If the connection has not been initialized yet, it calls `init_db()` to establish the connection first.
    Returns:
        Database: The MongoDB database instance.
    """
    global _db
    if _db is None:
        return init_db()
    return _db
