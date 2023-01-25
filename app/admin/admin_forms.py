"""Forms for Admin page"""
from wtforms import fields, validators, form as fo
from flask_admin.model.fields import InlineFieldList
from flask_admin.form import Select2Widget
from cosine_search.top_results import get_all_tags
import pandas as pd

from db.consts import DB_SERVICES
from db.mongo_connector import MongoConnector

# pylint: disable=W0702


def get_all_services():
    """Get all Questions"""
    m = MongoConnector(fsync=True)
    all_services = m.query_results_api(
        db=DB_SERVICES["db"],
        collection="questions",
        query={},
    )
    return all_services


def get_question_tags():
    """Get Tags from questions"""
    try:
        all_services = get_all_services()
        services = pd.DataFrame(all_services)
        g_t = services.main_tag.dropna().unique().tolist()
        tags = services.tags.explode().dropna().unique().tolist()
        values = set(g_t + tags)
        values = sorted(values)
    except:  # noqa: E722
        values = []
    return values


def get_service_question_tags():
    """Return Service and Question unique tags"""
    service_tags = get_all_tags()
    question_tags = get_question_tags()
    tags = sorted(set(service_tags + question_tags))
    return tags


CHOICES = [(str(x), x) for x in get_service_question_tags()]


class ServiceForm(fo.Form):
    """Service Form"""

    name = fields.StringField("Name")
    phone = fields.IntegerField("Phone", validators=[validators.Optional()])
    address = fields.StringField("Address", validators=[validators.Optional()])
    general_topic = fields.SelectField("General Topic", widget=Select2Widget())
    city = fields.StringField("City", validators=[validators.Optional()])
    state = fields.StringField("State", validators=[validators.Optional()])
    zip_code = fields.IntegerField("Zip Code", validators=[validators.Optional()])
    web_site = fields.StringField("Web Site", validators=[validators.Optional()])
    tags = InlineFieldList(fields.SelectField(choices=CHOICES, widget=Select2Widget()))


class QuestionForm(fo.Form):
    """Question Form"""

    question = fields.StringField("Name")
    main_tag = fields.SelectField("Main Tag", widget=Select2Widget())
    tags = InlineFieldList(fields.SelectField(choices=CHOICES, widget=Select2Widget()))


class AnalyticsForm(fo.Form):
    """Form for IP Hits"""

    ip_address = fields.StringField("IP ADDRESS")
    endpoint = fields.StringField("Endpoint")
    date = fields.DateTimeField("Date")


class UserForm(fo.Form):
    """User Form"""

    email = fields.StringField("email")
    password = fields.StringField("password")
    roles = InlineFieldList(
        fields.SelectField(choices=["user", "superuser"], widget=Select2Widget())
    )
