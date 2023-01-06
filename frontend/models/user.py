"""Postgres Models"""
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from frontend import db


class User(UserMixin, db.Model):
    """User account model."""

    __tablename__ = "flasklogin-users"
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), nullable=False, unique=False)
    password = db.Column(
        db.String(200), primary_key=False, unique=False, nullable=False
    )
    created_on = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    last_login = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    city = db.Column(db.String(200), index=False, unique=False, nullable=True)
    affiliation = db.Column(db.String(200), index=False, unique=False, nullable=True)

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password, method="sha256")

    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"<User {self.username}>"
