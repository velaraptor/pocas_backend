"""Forms for Admin page"""
from wtforms import fields, form as fo
from flask_admin.model.fields import InlineFieldList
from flask_admin.form import Select2Widget
from cosine_search.top_results import get_all_tags


TAGS = get_all_tags()
CHOICES = [(str(x), x) for x in TAGS]


class ServiceForm(fo.Form):
    """Service Form"""

    name = fields.StringField("Name")
    phone = fields.IntegerField("Phone")
    address = fields.StringField("Address")
    general_topic = fields.SelectField("General Topic", widget=Select2Widget())
    city = fields.StringField("City")
    state = fields.StringField("State")
    zip_code = fields.IntegerField("Zip Code")
    web_site = fields.StringField("Web Site")
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
    roles = InlineFieldList(fields.StringField())
