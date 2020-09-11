from db.consts import get_env_bool
from flask import Flask, url_for, redirect
from api.app import api_v1, limiter
from admin.app import admin
from flask_security import Security, MongoEngineUserDatastore, \
    UserMixin, RoleMixin, auth_required, hash_password
from flask_mongoengine import MongoEngine
from flask_admin import helpers as admin_helpers
import os
import secrets

app = Flask(__name__)
app.config['RESTX_MASK_SWAGGER'] = get_env_bool('RESTX_MASK_SWAGGER')
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.config['SECRET_KEY'] = secrets.token_urlsafe()
# Flask-Security config
app.config['SECURITY_URL_PREFIX'] = "/admin"
app.config['SECURITY_PASSWORD_SALT'] = os.environ.get("SECURITY_PASSWORD_SALT", '146585145368132386173505678016728509634')

# Flask-Security URLs, overridden because they don't put a / at the end
app.config['SECURITY_LOGIN_URL'] = "/login/"
app.config['SECURITY_LOGOUT_URL'] = "/logout/"

app.config['SECURITY_POST_LOGIN_VIEW'] = "/admin/"
app.config['SECURITY_POST_LOGOUT_VIEW'] = "/admin/"

# Flask-Security features
app.config['SECURITY_REGISTERABLE'] = False
app.config['SECURITY_SEND_REGISTER_EMAIL'] = False


username = os.getenv('MONGO_INITDB_ROOT_USERNAME')
password = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
host = os.getenv('MONGO_HOST')
port = os.getenv('MONGO_PORT')
app.config['MONGODB_SETTINGS'] = {
    'host': f'mongodb://{username}:{password}@{host}:{port}/users_login?authSource=admin'
}

db = MongoEngine(app)

class Role(db.Document, RoleMixin):
    name = db.StringField(max_length=80)
    description = db.StringField(max_length=255)

class User(db.Document, UserMixin):
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
    if get_env_bool('CREATE_USERS'):
        user_datastore.create_role(name='superuser', description='super user')
        user_datastore.create_role(name='user', description='normal user')
        user_datastore.create_user(email=os.getenv('ADMIN_USER'), password=hash_password(os.getenv('ADMIN_PASS')),
                                   roles=['superuser'])


# Views
@app.route('/')
@auth_required()
def home():
    return redirect(url_for('admin.index'))


@security.context_processor
def security_context_processor():
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )


app.register_blueprint(api_v1)
admin.init_app(app)
limiter.init_app(app)
