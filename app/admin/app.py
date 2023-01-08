"""Admin for Flask-Admin, includes Views"""
import uuid
from flask_admin import Admin, AdminIndexView
from flask_admin.menu import MenuLink
from flask_admin.contrib.pymongo import ModelView, filters
from flask_admin.contrib import sqla
from db.mongo_connector import MongoConnector
from db.consts import DB_SERVICES, get_lat_lon
from flask import url_for, redirect, request, abort
from flask_security import hash_password
from flask_security import current_user
from bson.dbref import DBRef
from werkzeug.security import generate_password_hash
from admin.admin_forms import ServiceForm, QuestionForm, AnalyticsForm, UserForm
from cosine_search.top_results import get_all_tags

# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611, W0223. R1725, W0221

conn = MongoConnector().client
db1 = conn[DB_SERVICES["db"]]

TAGS = get_all_tags()


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


class SuperSQLUserView(sqla.ModelView):
    """Postgres Model to look at MHP Users"""

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


class Analytics(SuperUserView):
    """Analytics View of hits"""

    column_list = ("ip_address", "endpoint", "date")
    column_searchable_list = ("ip_address", "endpoint")
    form = AnalyticsForm


class QuestionsView(MyModelView):
    """Questions Services"""

    column_list = ("id", "question", "tags", "main_tag")
    column_sortable_list = "id"
    column_filters = (
        filters.FilterLike("tags", "Tags"),
        filters.FilterLike("main_tag", "Main Tag"),
    )

    column_searchable_list = ("main_tag", "tags", "question")
    form = QuestionForm

    # Contribute list of user choices to the forms
    def _feed_tag_choices(self, form):
        form.main_tag.choices = [(str(x), x) for x in TAGS]
        return form

    def create_form(self):
        form = super(QuestionsView, self).create_form()
        return self._feed_tag_choices(form)

    def edit_form(self, obj):
        form = super(QuestionsView, self).edit_form(obj)
        return self._feed_tag_choices(form)

    def on_model_change(self, form, model, is_created):
        """On model change get id number"""
        collection = "questions"
        c = db1[collection]
        max_value = c.find().sort("id", -1).limit(1).next()
        model["id"] = max_value["id"] + 1

        return model


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
    column_filters = (
        filters.FilterLike("tags", "Tags"),
        filters.FilterLike("general_topic", "Main Tag"),
    )

    column_searchable_list = ("general_topic", "name", "tags", "city")
    form = ServiceForm

    def on_model_change(self, form, model, is_created):
        """On model change get lat/lon from Google API"""
        model = get_lat_lon(model)

        return model

    def _feed_tag_choices(self, form):
        form.general_topic.choices = [(str(x), x) for x in TAGS]
        return form

    def create_form(self):
        form = super(ServicesView, self).create_form()
        return self._feed_tag_choices(form)

    def edit_form(self, obj):
        form = super(ServicesView, self).edit_form(obj)
        return self._feed_tag_choices(form)


class MHPUsersView(SuperSQLUserView):
    """Users in MHP Portal Frontend"""

    column_list = [
        "user_name",
        "created_on",
        "last_login",
        "city",
        "affiliation",
    ]
    column_searchable_list = [
        "user_name",
        "city",
        "affiliation",
    ]
    form_widget_args = {"id": {"readonly": True}}

    def on_model_change(self, form, model, is_created):
        """Change Password on model change"""
        model.password = generate_password_hash(model.password, method="sha256")
        return model


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
    name="MHP Admin",
    url="/admin",
    index_view=MyAdminIndexView(template="home.html"),
    base_template="master.html",
    template_mode="bootstrap4",
)

admin.add_view(ServicesView(db1.services, "Services"))
admin.add_view(QuestionsView(db1.questions, "Questions"))
admin.add_view(Analytics(conn["analytics"].ip_hits, "Analytics"))
admin.add_view(UsersView(conn["users_login"]["user"], "Admin User Management"))
admin.add_link(MenuLink(name="POCAS API", url="/api/v1/docs", target="_blank"))
admin.add_link(MenuLink(name="MHP Portal", url="/login", target="_blank"))
