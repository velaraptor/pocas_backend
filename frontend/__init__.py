"""Flask App"""
import os
from flask import Flask
from frontend.views.main_view import main_blueprint
from frontend.models.flask_models import db, migrate, login_manager, cache


def create_app():
    """
    Initialize Flask app with Flask plugins
    """
    app = Flask(__name__)
    app.config.from_object(__name__)
    app.config["SECRET_KEY"] = "secret-key"
    app.config["RECAPTCHA_PUBLIC_KEY"] = os.getenv("RECAPTCHA_PUBLIC_KEY")
    app.config["RECAPTCHA_PRIVATE_KEY"] = os.getenv("RECAPTCHA_PRIVATE_KEY")
    POSTGRES_URI = (
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DBNAME')}"
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = POSTGRES_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    cache.init_app(app)
    app.register_blueprint(main_blueprint)

    return app
