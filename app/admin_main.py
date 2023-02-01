"""Admin Main for flask"""
import os
import secrets
from db.consts import get_env_bool
from flask import Flask, url_for, redirect
from flask_sqlalchemy import SQLAlchemy

from admin.app import admin, MHPUsersView
from flask_security import (
    Security,
    MongoEngineUserDatastore,
    UserMixin,
    RoleMixin,
    auth_required,
    hash_password,
)
from flask_mongoengine import MongoEngine
from flask_admin import helpers as admin_helpers


# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611, R0903

app = Flask(__name__)
app.config["FLASK_ADMIN_SWATCH"] = "litera"
app.config["SECRET_KEY"] = secrets.token_urlsafe()
# Flask-Security config
app.config["SECURITY_URL_PREFIX"] = "/admin/"
SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
app.config["SECURITY_PASSWORD_SALT"] = os.environ.get(
    "SECURITY_PASSWORD_SALT", "146585145368132386173505678016728509634"
)

# Flask-Security URLs, overridden because they don't put a / at the end
app.config["SECURITY_LOGIN_URL"] = "/admin/login/"
app.config["SECURITY_LOGOUT_URL"] = "/admin/logout/"

app.config["SECURITY_POST_LOGIN_VIEW"] = "/admin/"
app.config["SECURITY_POST_LOGOUT_VIEW"] = "/admin/"

# Flask-Security features
app.config["SECURITY_REGISTERABLE"] = False
app.config["SECURITY_SEND_REGISTER_EMAIL"] = False

username = os.getenv("MONGO_INITDB_ROOT_USERNAME")
password = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
host = os.getenv("MONGO_HOST")
port = os.getenv("MONGO_PORT")
app.config["MONGODB_SETTINGS"] = {
    "host": (
        f"mongodb://{username}:{password}@{host}:{port}/users_login?authSource=admin"
    )
}
POSTGRES_URI = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DBNAME')}"
)
app.config["SQLALCHEMY_DATABASE_URI"] = POSTGRES_URI
db = MongoEngine(app)
db_postgres = SQLAlchemy(app)


class Role(db.Document, RoleMixin):
    """SQLAlchemy Role"""

    name = db.StringField(max_length=80)
    description = db.StringField(max_length=255)


class MHPUser(db_postgres.Model):
    """User account model."""

    __tablename__ = "flasklogin-users"
    id = db_postgres.Column(db_postgres.Integer, primary_key=True)
    user_name = db_postgres.Column(
        db_postgres.String(100), nullable=False, unique=False
    )
    password = db_postgres.Column(
        db_postgres.String(200), primary_key=False, unique=False, nullable=False
    )
    created_on = db_postgres.Column(
        db_postgres.DateTime, index=False, unique=False, nullable=True
    )
    last_login = db_postgres.Column(
        db_postgres.DateTime, index=False, unique=False, nullable=True
    )
    city = db_postgres.Column(
        db_postgres.String(200), index=False, unique=False, nullable=True
    )
    affiliation = db_postgres.Column(
        db_postgres.String(200), index=False, unique=False, nullable=True
    )


class User(db.Document, UserMixin):
    """SQLAlchemy User"""

    email = db.StringField(max_length=255)
    password = db.StringField(max_length=255)
    active = db.BooleanField(default=True)
    fs_uniquifier = db.StringField(max_length=255)
    confirmed_at = db.DateTimeField()
    roles = db.ListField(default=[])


user_datastore = MongoEngineUserDatastore(db, User, Role)
security = Security(app, user_datastore)


# Create a user to test with
@app.before_first_request
def create_user():
    """Create User if first time and Env is set"""
    if get_env_bool("CREATE_USERS"):
        user_datastore.create_role(name="superuser", description="super user")
        user_datastore.create_role(name="user", description="normal user")
        user_datastore.create_user(
            email="christophvel@gmail.com",
            password=hash_password("chris"),
            roles=["superuser"],
        )


# Views
@app.route("/")
@auth_required()
def home():
    """Admin redirect from base /"""
    return redirect(url_for("admin.index"))


@security.context_processor
def security_context_processor():
    """Security Context for Flask-Login to work with Flask-Admin"""
    return {
        "admin_base_template": admin.base_template,
        "admin_view": admin.index_view,
        "h": admin_helpers,
        "get_url": url_for,
    }


admin.add_view(
    MHPUsersView(MHPUser, db_postgres.session, name="MHP Users", category="Tools")
)
admin.init_app(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
