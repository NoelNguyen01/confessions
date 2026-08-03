from main import create_app
from os import getenv

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(getenv("PORT", 3000)))
