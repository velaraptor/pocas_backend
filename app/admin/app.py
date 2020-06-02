from flask_admin import Admin, AdminIndexView
from flask_admin.menu import MenuLink
from wtforms import form, fields
from db.mongo_connector import MongoConnector
from flask_admin.contrib.pymongo import ModelView
from flask_admin.model.fields import InlineFieldList
from db.consts import DB_SERVICES, get_lat_lon
import os
from flask_security import current_user
from flask import  url_for, redirect, request, abort

conn = MongoConnector().client
db = conn[DB_SERVICES['db']]


# Create customized model view class
class MyModelView(ModelView):
    def is_accessible(self):
        return (current_user.is_active and
                current_user.is_authenticated
                )

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


# Create customized index view class
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return (current_user.is_active and
                current_user.is_authenticated
                )

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


class ServiceForm(form.Form):
    name = fields.StringField('name')
    phone = fields.IntegerField('phone')
    address = fields.StringField('address')
    general_topic = fields.StringField('general_topic')
    city = fields.StringField('city')
    state = fields.StringField('state')
    zip_code = fields.IntegerField('zip_code')
    web_site = fields.StringField('web_site')
    tags = InlineFieldList(fields.StringField())


class ServicesView(MyModelView):
    column_list = ('name', 'phone', 'address', 'lat', 'lon', 'general_topic', 'city', 'state', 'zip_code', 'web_site', 'tags')
    column_sortable_list = ('name', 'phone', 'address', 'general_topic', 'city', 'state', 'zip_code')

    form = ServiceForm

    def on_model_change(self, form, model, is_created):
        model = get_lat_lon(model)

        return model

VERSION = os.getenv('VERSION')
admin = Admin(name='POCAS Admin Panel', url='/admin', index_view=MyAdminIndexView(
        template='home.html'
    ), base_template='my_master.html', template_mode='bootstrap3')
admin.add_view(ServicesView(db[DB_SERVICES['collection']], 'Services Importer'))
admin.add_link(MenuLink(name='POCAS API', url=f'/api/v{VERSION}/'))
