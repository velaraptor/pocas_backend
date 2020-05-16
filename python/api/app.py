from flask import Flask
from flask_restx import Api, Resource, fields
import os


app = Flask(__name__)
api = Api(app, version=os.getenv('VERSION'), title='POCAS API',
    description='an api to get data',
)

ns = api.namespace('person', description='TODO operations')


if __name__ == '__main__':
    app.run(debug=True, port=80, host='0.0.0.0')