from flask_wtf import FlaskForm
from flask_wtf.recaptcha import RecaptchaField
import requests
from wtforms import PasswordField, StringField, SubmitField, BooleanField, DateField, SelectMultipleField
from flask_bootstrap import SwitchField
from wtforms.validators import DataRequired, EqualTo, Length
import pandas as pd


def get_tags():
    services_resp = requests.get('http://pocas_api/services')
    services = pd.DataFrame(services_resp.json()['services'])
    g_t = services.general_topic.dropna().unique().tolist()
    tags = services.tags.explode().dropna().unique().tolist()
    return set(g_t + tags)


class Tags(FlaskForm):
    tags = SelectMultipleField(
        'Filter by Tags',
        choices=get_tags()
    )


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


class Questions(FlaskForm):
    dob = DateField(
        'DOB',
        validators=[
            DataRequired()
        ]
    )
    zip_code = StringField(
        'Zip Code',
        validators=[
            DataRequired(),
            Length(min=5, max=5)
        ]

    )
    question_2 = SwitchField(
        """Is anyone scaring, threatening or hurting you or your children?"""
    )
    question_3 = SwitchField(
        """Every family has fights.  What are fights like in your home? """
    )
    question_4 = SwitchField(
        """Do you ever skip or cut the dose of a medicine because of cost? """
    )
    question_5 = SwitchField(
        """Do you and your family have health insurance?  If not, have you applied for AHCCCS, KidsCare, ACA insurance or other benefits? """
    )
    question_6 = SwitchField(
        """Are you pregnant?  If so, have you spoken to anyone about WIC?"""
    )
    question_7 = SwitchField(
        """If you have applied for assistance and been denied, have you filed an appeal?"""
    )
    question_8 = SwitchField(
        """Are you working?"""
    )
    question_9 = SwitchField(
        """Do you always have enough food to eat?"""
    )
    question_10 = SwitchField(
        """Are you receiving benefits from programs such as Cash Assistance or Food Stamps?"""
    )
    question_11 = SwitchField(
        """In the last year, have you worried that food would run out before you got money to buy more?"""
    )
    question_12 = SwitchField(
        """Are you or anyone in your family >65, blind or disabled?"""
    )
    question_13 = SwitchField(
        """Have you applied for SSI /SSDI benefits?"""
    )
    question_14 = SwitchField(
        """Do you have concerns/problems with your home?"""
    )
    question_15 = SwitchField(
        """Do you have any problems with your landlord?"""
    )
    question_16 = SwitchField(
        """Do you have mold, mice or roaches in your home?"""
    )
    question_17 = SwitchField(
        """Was your home built before 1978?"""
    )
    question_18 = SwitchField(
        """Do you have peeling/chipping paint in your home?"""
    )
    question_19 = SwitchField(
        """Do you have smoke and CO2 detectors?"""
    )
    question_20 = SwitchField(
        """How are your children doing in school?"""
    )
    question_21 = SwitchField(
        """Are they failing or struggling in any classes?"""
    )
    question_22 = SwitchField(
        """Do they have problems getting along with other children or teachers?"""
    )
    question_23 = SwitchField(
        """How often do they miss school?"""
    )
    question_24 = SwitchField(
        """Does your child have a disability?"""
    )
    question_25 = SwitchField(
        """Has your child been evaluated for special education services?"""
    )
    question_26 = SwitchField(
        """Does your child have an Individual Education Program (IEP) or Section 504 plan?"""
    )
    question_27 = SwitchField(
        """Would you like to discuss any legal problems with an attorney at no cost?"""
    )
    question_28 = SwitchField(
        """Identify as LBTQ?"""
    )
    question_29 = SwitchField(
        """Identify as Indigent?"""
    )
    question_30 = SwitchField(
        """Need transportation?"""
    )

    submit = SubmitField('Submit')
