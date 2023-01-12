"""Initialze Flask Models"""
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
migrate = Migrate()
cache = Cache(config={"CACHE_TYPE": "SimpleCache"})
login_manager = LoginManager()
jwt = JWTManager()
mail = Mail()
