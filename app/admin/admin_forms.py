"""Forms for Admin page"""
from wtforms import fields, form as fo
from flask_admin.model.fields import InlineFieldList


class ServiceForm(fo.Form):
    """Service Form"""

    name = fields.StringField("Name")
    phone = fields.IntegerField("Phone")
    address = fields.StringField("Address")
    general_topic = fields.StringField("General Topic")
    city = fields.StringField("City")
    state = fields.StringField("State")
    zip_code = fields.IntegerField("Zip Code")
    web_site = fields.StringField("Web Site")
    tags = InlineFieldList(fields.StringField())


class QuestionForm(fo.Form):
    """Question Form"""

    question = fields.StringField("Name")
    id = fields.IntegerField("id")
    main_tag = fields.StringField("Main Tag")
    tags = InlineFieldList(fields.StringField())


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
