from main import create_app
from os import getenv

app = create_app()

if __name__ == "__main__":
    app.run(port=int(getenv("PORT", 3000)))
