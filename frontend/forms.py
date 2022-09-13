from flask_wtf import FlaskForm
from flask_wtf.recaptcha import RecaptchaField

from wtforms import PasswordField, StringField, SubmitField, SelectField, BooleanField, IntegerField, \
    widgets, SelectMultipleField
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange


class SignupForm(FlaskForm):
    """User Sign-up Form."""
    user_name = StringField(
        'User Name',
        validators=[DataRequired()]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(),
            Length(min=6, message='Select a stronger password.')
        ]
    )
    confirm = PasswordField(
        'Confirm Your Password',
        validators=[
            DataRequired(),
            EqualTo('password', message='Passwords must match.')
        ]
    )
    recaptcha = RecaptchaField()
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    """User Log-in Form."""
    user_name = StringField(
        'User Name',
        validators=[
            DataRequired(),
        ]
    )
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField()
    submit = SubmitField('Login')
