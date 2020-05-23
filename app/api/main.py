from db.consts import get_env_bool
from flask import Flask
from api.app import api_v1
from admin.app import admin
import os


app = Flask(__name__)
app.config['RESTX_MASK_SWAGGER'] = get_env_bool('RESTX_MASK_SWAGGER')
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.config['SECRET_KEY'] = '123456790'

app.config['MONGODB_SETTINGS'] = {'DB': 'user', 'HOST': os.getenv('MONGO_HOST'),
                                  'PORT': int(os.getenv('MONGO_PORT')),
                                  'PASSWORD': os.getenv('MONGO_INITDB_ROOT_PASSWORD'),
                                  'USERNAME': os.getenv('MONGO_INITDB_ROOT_USERNAME')}

app.register_blueprint(api_v1)
admin.init_app(app)