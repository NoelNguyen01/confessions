import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from config import Config
from flask import Flask
from src.routes import register_blueprints


def create_app():

    app = Flask(__name__)

    app.config.from_object(Config)

    register_blueprints(app)

    return app
