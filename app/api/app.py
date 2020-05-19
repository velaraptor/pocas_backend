from flask import Flask, Blueprint
from flask_restx import Api, Resource, fields
from cosine_search import top_results as tr
from db.mongo_connector import MongoConnector
import os

VERSION = os.getenv('VERSION')
api_v1 = Blueprint('api', __name__, url_prefix=f'/api/v{VERSION}/')
api = Api(api_v1, version='v%s' % VERSION, title='POCAS API',
          description='an api to get results for pocas',
          )

ns = api.namespace('top_results', description='recieve questionaire and get results')


top_results = api.model(
    'TopResults', {'id': fields.Integer(required=True, description="Unique id of Service", example=1),
                   'name': fields.String(required=True, description="The Name of Service", example='Indigent Legal Fund'),
                   'phone': fields.Integer(required=True, description="Phone Number of service", example=5551114444),
                   'address': fields.String(required=False, description="the address of service", example='1111 S 1st'),
                   'general_topic': fields.String(required=True, description="the general topic service belongs to",
                                                  example='Immigration'),
                   'tags': fields.List(fields.String(required=False, description='tag', example='Young Adult'),
                                       required=True, description='tags associated'),
                   'city': fields.String(required=False, description="city service is in", example='Tuscon'),
                   'state': fields.String(required=False, description="state service is in", example='AZ'),
                   'lat': fields.Float(required=False, description="Latitude coordinates", example=72.34),
                   'lon': fields.Float(required=False, description="Longitude coordinates", example=34.01),
                   'zip_code': fields.Integer(required=False, description='zip code for service', example=78724),
                   'web_site': fields.String(required=False, description='web site for service',
                                             example='http://www.example.com'),
                   'pocas_score': fields.Float(required=True,
                                               description='score for ordering results, higher is better',
                                               example=0.12)
                   }
)


parser = api.parser()
# TODO; change these args
parser.add_argument(
    "address", type=str, required=True, help="the address"
)
parser.add_argument(
    "dob", type=int, required=True, help="the date of birth", location="form"
)
parser.add_argument(
    "question_answers", type=str, required=True, help="the answer to question", location="form"
)

TEST = {'id': 1, 'name': 'test', 'phone': 5551114444, 'general_topic': 'test', 'tags': ['tag1', 'tag2'],
        'web_site': 'http://www.example.com', 'pocas_score': 0.98}


@ns.route("/")
class TopResults(Resource):
    @api.doc(parser=parser)
    @api.marshal_with(top_results)
    def post(self):
        """
        Send questionnaire and get Top N results
        """
        args = parser.parse_args()
        return TEST

    @api.marshal_with(top_results)
    def get(self):
        """
        Get all Services for POCAS
        """
        m = MongoConnector()
        results = m.query_results(db='results', collection='services', query={})
        if len(results) > 0:
            return results, 201
        else:
            return None, 404


if __name__ == '__main__':
    app = Flask(__name__)
    app.config['RESTX_MASK_SWAGGER'] = os.getenv('RESTX_MASK_SWAGGER', False)
    app.register_blueprint(api_v1)
    app.run(debug=True, port=80, host='0.0.0.0')
