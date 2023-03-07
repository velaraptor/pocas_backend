"""Postgres Models"""
import os
import traceback
from time import time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import jwt
from frontend.models.flask_models import db
from frontend.setup_logging import logger


class User(UserMixin, db.Model):
    """User account model."""

    __tablename__ = "flasklogin-users"
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=True, unique=True)
    password = db.Column(
        db.String(200), primary_key=False, unique=False, nullable=False
    )
    created_on = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    last_login = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    city = db.Column(db.String(200), index=False, unique=False, nullable=True)
    search_city = db.Column(db.String(200), index=False, unique=False, nullable=True)
    affiliation = db.Column(db.String(200), index=False, unique=False, nullable=True)

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password, method="sha256")

    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)

    @staticmethod
    def verify_reset_token(token):
        """Verify JWT Reset Token"""
        try:
            username = jwt.decode(
                token, key=os.getenv("FLASK_SECRET_KEY"), algorithms="HS256"
            )["reset_password"]
        except Exception:
            logger.warning(traceback.format_exc())
            return None
        return User.query.filter_by(user_name=username).first()

    def get_reset_token(self, expires=500):
        """Create JWT Token to send with Recovery Email"""
        return jwt.encode(
            {"reset_password": self.user_name, "exp": time() + expires},
            key=os.getenv("FLASK_SECRET_KEY"),
            algorithm="HS256",
        )

    @staticmethod
    def verify_email(email):
        """Verify Email User"""
        user = User.query.filter_by(email=email).first()
        return user

    def __repr__(self):
        return f"<User {self.user_name}>"
