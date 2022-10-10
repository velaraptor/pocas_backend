"""Admin for Flask-Admin, includes Views"""
import uuid
from flask_admin import Admin, AdminIndexView
from flask_admin.menu import MenuLink
from flask_admin.contrib.pymongo import ModelView
from flask_admin.model.fields import InlineFieldList
from wtforms import fields, form as fo
from db.mongo_connector import MongoConnector
from db.consts import DB_SERVICES, get_lat_lon
from flask import url_for, redirect, request, abort
from flask_security import hash_password
from flask_security import current_user
from bson.dbref import DBRef

# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611, W0223

conn = MongoConnector().client
db1 = conn[DB_SERVICES["db"]]


class MyModelView(ModelView):
    """Generic Model View to include authentication"""

    def is_accessible(self):
        return current_user.is_active and current_user.is_authenticated

    def _handle_view(self, name, **kwargs):  # pylint: disable=R1710
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for("security.login", next=request.url))


class SuperUserView(MyModelView):
    """Generic Model View to include authentication for superuser"""

    def is_accessible(self):
        return (
            current_user.is_active
            and current_user.is_authenticated
            and current_user.has_role("superuser")
        )


class MyAdminIndexView(AdminIndexView):
    """Generic Model View to include authentication for Index View"""

    def is_accessible(self):
        return current_user.is_active and current_user.is_authenticated

    def _handle_view(self, name, **kwargs):  # pylint: disable=R1710
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for("security.login", next=request.url))


class ServiceForm(fo.Form):
    """Service Form"""

    name = fields.StringField("name")
    phone = fields.IntegerField("phone")
    address = fields.StringField("address")
    general_topic = fields.StringField("general_topic")
    city = fields.StringField("city")
    state = fields.StringField("state")
    zip_code = fields.IntegerField("zip_code")
    web_site = fields.StringField("web_site")
    tags = InlineFieldList(fields.StringField())


class QuestionForm(fo.Form):
    """Question Form"""

    question = fields.StringField("name")
    id = fields.IntegerField("id")
    main_tag = fields.StringField("main_tag")
    tags = InlineFieldList(fields.StringField())


class AnalyticsForm(fo.Form):
    """Form for IP Hits"""

    ip_address = fields.StringField("ip_address")
    endpoint = fields.StringField("endpoint")
    date = fields.DateTimeField("Date")


class Analytics(SuperUserView):
    """Analytics View of hits"""

    column_list = ("ip_address", "endpoint", "date")
    column_searchable_list = ("ip_address", "endpoint")
    form = AnalyticsForm


class QuestionsView(MyModelView):
    """Questions Services"""

    column_list = ("id", "question", "tags", "main_tag")
    column_sortable_list = "id"

    form = QuestionForm


class ServicesView(MyModelView):
    """POCAS Services"""

    column_list = (
        "name",
        "phone",
        "address",
        "lat",
        "lon",
        "general_topic",
        "city",
        "state",
        "zip_code",
        "web_site",
        "tags",
    )
    column_sortable_list = (
        "name",
        "phone",
        "address",
        "general_topic",
        "city",
        "state",
        "zip_code",
    )

    form = ServiceForm

    def on_model_change(self, form, model, is_created):
        """On model change get lat/lon from Google API"""
        model = get_lat_lon(model)

        return model


class UserForm(fo.Form):
    """User Form"""

    email = fields.StringField("email")
    password = fields.StringField("password")
    roles = InlineFieldList(fields.StringField())


class UsersView(SuperUserView):
    """Users in Flask Admin"""

    column_list = ("email", "active", "fs_uniquifier", "roles")
    column_sortable_list = ("email", "active", "fs_uniquifier", "roles")
    form = UserForm

    def on_model_change(self, form, model, is_created):
        """Change Password, role on model change"""
        model["password"] = hash_password(model["password"])
        model["active"] = True
        model["fs_uniquifier"] = uuid.uuid4().hex

        valid_roles = []
        if model.get("roles", []):
            for role in model.get("roles"):
                mongo_roles = MongoConnector().query_results(
                    db="users_login", collection="role", query={"name": role}
                )
                if len(mongo_roles) > 0:
                    valid_roles.append(
                        DBRef(collection="role", id=mongo_roles[0]["_id"])
                    )

        model["roles"] = valid_roles
        return model


# TODO: ADD import csv https://blog.sneawo.com/blog/2018/02/16/export-and-import-for-mongoengine-model-in-flask-admin/
# TODO: add user management from frontend

admin = Admin(
    name="POCAS Admin Panel",
    url="/admin",
    index_view=MyAdminIndexView(template="home.html"),
    base_template="master.html",
    template_mode="bootstrap3",
)

admin.add_view(ServicesView(db1.services, "Services Importer"))
admin.add_view(Analytics(conn["analytics"].ip_hits, "API Analytics"))
admin.add_view(UsersView(conn["users_login"]["user"], "Admin User Management"))
admin.add_view(QuestionsView(db1.questions, "Questions Editor"))
admin.add_link(MenuLink(name="POCAS API", url="/api/v1/docs"))
