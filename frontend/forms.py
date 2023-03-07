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
    SelectField,
)
from wtforms.validators import InputRequired, EqualTo, Length, Email, NumberRange
import pandas as pd
from frontend.consts import API_URL  # pylint: disable=import-error
from frontend.setup_logging import logger

CITY_CHOICES = ["", "Tucson, AZ"]


def get_tags():
    """Get Tags from POCAS API and get unique ones"""
    try:
        services_resp = requests.get(f"{API_URL}services", timeout=5)
        services = pd.DataFrame(services_resp.json()["services"])
        g_t = services.general_topic.dropna().unique().tolist()
        tags = services.tags.explode().dropna().unique().tolist()
        values = set(g_t + tags)
        values = sorted(values)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e) from e
    except Exception as e:
        logger.warning(str(e), exc_info=True)
        values = []
    return values


class Tags(FlaskForm):
    """Form to filter by tags in services map"""

    tags = SelectMultipleField("Filter by Tags", choices=get_tags())


class EditForm(FlaskForm):
    """Edit User Profile"""

    city = StringField("City", validators=[InputRequired()])
    affiliation = StringField("Affiliation")
    email = StringField("Email", validators=[InputRequired(), Email()])
    search_city = SelectField("Search City", choices=CITY_CHOICES)
    submit = SubmitField("Save Changes")


class ChangePassForm(FlaskForm):
    """Change Password Form"""

    old_password = PasswordField(
        "Old Password",
        validators=[
            InputRequired(),
            Length(min=6, message="Select a stronger password."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            InputRequired(),
            Length(min=6, message="Select a stronger password."),
        ],
    )
    confirm = PasswordField(
        "Confirm Your Password",
        validators=[
            InputRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )


class SignupForm(FlaskForm):
    """User Sign-up Form."""

    user_name = StringField("User Name", validators=[InputRequired()])
    password = PasswordField(
        "Password",
        validators=[
            InputRequired(),
            Length(min=6, message="Select a stronger password."),
        ],
    )
    email = StringField("Email", validators=[InputRequired(), Email()])
    city = StringField("City", validators=[InputRequired()])
    affiliation = StringField("Affiliation")
    confirm = PasswordField(
        "Confirm Your Password",
        validators=[
            InputRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    """User Log-in Form."""

    user_name = StringField(
        "User Name",
        validators=[
            InputRequired(),
        ],
    )
    password = PasswordField("Password", validators=[InputRequired()])
    remember = BooleanField()
    submit = SubmitField("Login")


class Questions(FlaskForm):
    """Questions for POCAS"""

    age = IntegerField(
        "Age",
        validators=[
            InputRequired(),
            NumberRange(min=0, max=150, message="Age Must be between 0 and 150!"),
        ],
    )
    zip_code = StringField(
        "Zip Code",
        validators=[
            InputRequired(),
            Length(min=5, max=5, message="Zip Code length must be %(max)d characters"),
        ],
    )
    submit = SubmitField("Submit")


class SearchServices(FlaskForm):
    """Search Form"""

    search_city = SelectField("Search City", choices=CITY_CHOICES)
    remember = BooleanField()

    submit = SubmitField("Submit")
