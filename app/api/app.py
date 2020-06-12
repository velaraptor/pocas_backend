import os

from flask import Flask, Blueprint, request
from flask_restx import Api, Resource, fields
from cosine_search.top_results import GetTopNResults
from db.mongo_connector import MongoConnector
from db.upload_data import main as upload_data
from db.consts import get_env_bool, DB_SERVICES, get_lat_lon
import logging


logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] %(name)s [%(levelname)s]: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

VERSION = os.getenv('VERSION')
api_v1 = Blueprint('api', __name__, url_prefix=f'/api/v{VERSION}/')
api = Api(api_v1, version='v%s' % VERSION, title='POCAS API',
          description='an api to get results for pocas', authorizations=authorizations, security='apikey'
          )

ns = api.namespace('services', description='recieve questionaire and get results')


top_n_model = api.model('PatientInfo',
                        {'dob': fields.Integer(required=True,
                                               description='Date of Birth in integer such 12252011',
                                               example=12252011),
                         'address': fields.String(required=True,
                                                  description='Address with City State',
                                                  example='1111 S 1st Tuscon AZ'),
                         'answers': fields.List(
                             fields.Integer(description='Answers to Questionnaire Question', example=1), required=True,
                                                description='List of answers to Questionnaire',
                             example=[1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                      0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1]),
                         'top_n': fields.Integer(required=True,
                                                 description='Top N Services to Return',
                                                 example=2)
                         })
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
                'zip_code': fields.Float(required=False, description='zip code for service', example=78724.0),
                'web_site': fields.String(required=False, description='web site for service',
                                          example='http://www.example.com'),
                'online_service': fields.Integer(required=False, description='Binary for Online Service'),
                'hours': fields.String(description='Hours'),
                'days': fields.String(description='Days'),
                'pocas_score': fields.Float(required=False,
                                            description='score for ordering results, higher is better',
                                            example=0.12)
                }
)

results = api.model('TopResults', {'services': fields.List(fields.Nested(services)),
                                   'num_of_services': fields.Integer(required=True, example=1)})

success_service = api.model('MongoId',
                            {'id': fields.String(required=True,
                                                 description='Id of Service on MongoDB')})

post_service = api.model(
    'ServiceUpload', {
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
                                          example='http://www.example.com')
                }
)

@ns.route("/")
class Services(Resource):
    @api.marshal_with(results, skip_none=True)
    @api.response(404, "Results not found")
    @api.response(401, "Unauthorized key!")
    def get(self):
        """
        Get all Services for POCAS
        """
        if request.headers.get('X-API-KEY', '') != os.getenv('API_SECRET'):
            api.abort(401)
        ns.logger.info("Ran Get Method")
        m = MongoConnector()
        all_services = m.query_results(db=DB_SERVICES['db'], collection=DB_SERVICES['collection'],
                                       query={}, exclude={'loc': 0})
        for r in all_services:
            r['id'] = str(r['_id'])
            r.pop('_id', None)
        num_docs = len(all_services)
        if num_docs > 0:
            response = {'services': all_services, 'num_of_services': num_docs}
            return response, 200
        else:
            api.abort(404)

    @api.expect(post_service, skip_none=True)
    @api.marshal_with(success_service, skip_none=True)
    @api.response(401, "Unauthorized key!")
    def post(self):
        """
        Upload Service to MongoDB
        :return:
        """
        if request.headers.get('X-API-KEY', '') != os.getenv('API_SECRET'):
            api.abort(401)
        ns.logger.info("Ran Post Method")
        m = MongoConnector()
        payload = api.payload
        payload = get_lat_lon(payload)
        mongo_id = m.upload_results(db=DB_SERVICES['db'], collection=DB_SERVICES['collection'], data=[payload])
        return {'id': mongo_id[0]}, 200

@ns.route('/top_n')
class TopNResults(Resource):
    @api.expect(top_n_model)
    @api.marshal_with(results, skip_none=True)
    @api.response(404, "Results not found")
    @api.response(401, "Unauthorized key!")
    def post(self):
        """
        Send questionnaire and get Top N results
        """
        if request.headers.get('X-API-KEY', '') != os.getenv('API_SECRET'):
            api.abort(401)
        ns.logger.info("Ran Post Method")
        top_n = api.payload['top_n']
        dob = api.payload['dob']
        answers = api.payload['answers']
        address = api.payload['address']
        try:
            assert len(answers) == 30
            gtr = GetTopNResults(top_n=top_n, dob=dob, answers=answers, address=address)
            top_services = gtr.get_top_results()
            for r in top_services:
                r['id'] = str(r['_id'])
                r.pop('_id', None)
            assert len(top_services) <= int(top_n)
            return {'services': top_services, 'num_of_services': len(top_services)}, 200
        except Exception as e:
            ns.logger.error(e)
            api.abort(404)

if __name__ == '__main__':
    # upload data
    rerun_upload_services = get_env_bool('RERUN_SERVICES')
    if rerun_upload_services:
        upload_data()

    app = Flask(__name__)
    app.config['RESTX_MASK_SWAGGER'] = get_env_bool('RESTX_MASK_SWAGGER')
    app.register_blueprint(api_v1)
    app.run(debug=True, port=80, host='0.0.0.0')
