"""Initialze Flask Models"""
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
cache = Cache(config={"CACHE_TYPE": "SimpleCache"})
login_manager = LoginManager()
