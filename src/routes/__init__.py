from src.routes.get_data import data_bp
from src.routes.post_facebook import post_bp

all_blueprints = {
    "": [data_bp, post_bp],
}


def register_blueprints(app):
    for prefix, blueprints in all_blueprints.items():

        if not isinstance(blueprints, list):
            blueprints = [blueprints]

        for bp in blueprints:
            app.register_blueprint(bp, url_prefix=prefix if prefix else None)
