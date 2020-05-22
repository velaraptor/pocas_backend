from db.consts import get_env_bool
from flask import Flask
from api.app import api_v1

app = Flask(__name__)
app.config['RESTX_MASK_SWAGGER'] = get_env_bool('RESTX_MASK_SWAGGER')
app.register_blueprint(api_v1)
