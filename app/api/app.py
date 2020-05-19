import os

from flask import Flask, Blueprint
from flask_restx import Api, Resource, fields
from cosine_search.top_results import GetTopNResults
from db.mongo_connector import MongoConnector
from db.upload_data import main as upload_data
from db.consts import get_env_bool, DB_SERVICES

VERSION = os.getenv('VERSION')
api_v1 = Blueprint('api', __name__, url_prefix=f'/api/v{VERSION}/')
api = Api(api_v1, version='v%s' % VERSION, title='POCAS API',
          description='an api to get results for pocas',
          )

ns = api.namespace('services', description='recieve questionaire and get results')

services = api.model(
    'Service', {'id': fields.String(required=True, description="Unique id of Service", example='1fjdasd'),
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
                'pocas_score': fields.Float(required=False,
                                            description='score for ordering results, higher is better',
                                            example=0.12)
                }
)

results = api.model('TopResults', {'services': fields.List(fields.Nested(services)),
                                   'num_of_services': fields.Integer(required=True, example=1)})

parser = api.parser()
parser.add_argument(
    "address", type=str, required=True, help="the address"
)
parser.add_argument(
    "dob", type=int, required=True, help="the date of birth")

# TODO; change these args
parser.add_argument(
    "question_answers", type=str, required=True, help="the answer to question"
)
parser.add_argument(
    "top_n", type=int, required=True, help="top n results"
)


@ns.route("/")
class Services(Resource):
    @api.marshal_with(results)
    def get(self):
        """
        Get all Services for POCAS
        """
        m = MongoConnector()
        all_services = m.query_results(db=DB_SERVICES['db'], collection=DB_SERVICES['collection'],
                                       query={}, exclude={'loc': 0})
        for r in all_services:
            r['id'] = str(r['_id'])
            r.pop('_id', None)
        num_docs = len(all_services)
        if num_docs > 0:
            response = {'services': all_services, 'num_of_services': num_docs}
            return response, 201
        else:
            return None, 404


@ns.route('/top_n')
class TopNResults(Resource):
    @api.doc(parser=parser)
    @api.marshal_with(results)
    def post(self):
        """
        Send questionnaire and get Top N results
        """
        args = parser.parse_args()
        top_n = args['top_n']
        dob = args['dob']
        address = args['address']
        answers = args['question_answers']
        gtr = GetTopNResults(top_n=top_n, dob=dob, answers=answers, address=address)
        top_services = gtr.get_top_results()
        for r in top_services:
            r['id'] = str(r['_id'])
            r.pop('_id', None)
        return {'services': top_services, 'num_of_services': len(top_services)}


if __name__ == '__main__':
    # upload data
    rerun_upload_services = get_env_bool('RERUN_SERVICES')
    if rerun_upload_services:
        upload_data()

    app = Flask(__name__)
    app.config['RESTX_MASK_SWAGGER'] = get_env_bool('RESTX_MASK_SWAGGER')
    app.register_blueprint(api_v1)
    app.run(debug=True, port=80, host='0.0.0.0')
