from flask_admin import Admin
from wtforms import form, fields
from db.mongo_connector import MongoConnector
from flask_admin.contrib.pymongo import ModelView
from flask_admin.model.fields import InlineFieldList
from db.consts import DB_SERVICES, get_lat_lon
# TODO add to talk to top_n, add auth

conn = MongoConnector().client
db = conn[DB_SERVICES['db']]


class InnerForm(form.Form):
    fields.StringField()

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



class ServicesView(ModelView):
    column_list = ('name', 'phone', 'address', 'lat', 'lon', 'general_topic', 'city', 'state', 'zip_code', 'web_site', 'tags')
    column_sortable_list = ('name', 'phone', 'address', 'general_topic', 'city', 'state', 'zip_code')

    form = ServiceForm

    def on_model_change(self, form, model, is_created):
        model = get_lat_lon(model)

        return model

admin = Admin(name='POCAS Admin Panel', url='/admin')
admin.add_view(ServicesView(db[DB_SERVICES['collection']], 'Services Importer'))
