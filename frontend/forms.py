"""Forms for Frontend"""
# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611

from flask_wtf import FlaskForm
import requests
from wtforms import (
    PasswordField,
    StringField,
    SubmitField,
    BooleanField,
    IntegerField,
    SelectMultipleField,
)
from wtforms.validators import DataRequired, EqualTo, Length, Email
import pandas as pd
from frontend.consts import API_URL  # pylint: disable=import-error


def get_tags():
    """Get Tags from POCAS API and get unique ones"""
    try:
        services_resp = requests.get(f"{API_URL}services", timeout=20)
        services = pd.DataFrame(services_resp.json()["services"])
        g_t = services.general_topic.dropna().unique().tolist()
        tags = services.tags.explode().dropna().unique().tolist()
        tags = tags + [" "]
        values = set(g_t + tags)
        values = sorted(values)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e) from e
    except Exception as e:
        print(str(e))
        values = []
    return values


class Tags(FlaskForm):
    """Form to filter by tags in services map"""

    tags = SelectMultipleField("Filter by Tags", choices=get_tags())


class EditForm(FlaskForm):
    """Edit User Profile"""

    city = StringField("City", validators=[DataRequired()])
    affiliation = StringField("Affiliation")
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Save Changes")


class ChangePassForm(FlaskForm):
    """Change Password Form"""

    old_password = PasswordField(
        "Old Password",
        validators=[
            DataRequired(),
            Length(min=6, message="Select a stronger password."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=6, message="Select a stronger password."),
        ],
    )
    confirm = PasswordField(
        "Confirm Your Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )


class SignupForm(FlaskForm):
    """User Sign-up Form."""

    user_name = StringField("User Name", validators=[DataRequired()])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=6, message="Select a stronger password."),
        ],
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    city = StringField("City", validators=[DataRequired()])
    affiliation = StringField("Affiliation")
    confirm = PasswordField(
        "Confirm Your Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    """User Log-in Form."""

    user_name = StringField(
        "User Name",
        validators=[
            DataRequired(),
        ],
    )
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField()
    submit = SubmitField("Login")


class Questions(FlaskForm):
    """Questions for POCAS"""

    age = IntegerField("Age", validators=[DataRequired()])
    zip_code = StringField(
        "Zip Code", validators=[DataRequired(), Length(min=5, max=5)]
    )
    submit = SubmitField("Submit")
