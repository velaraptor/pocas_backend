from fastapi import FastAPI, HTTPException, Depends,status
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi.middleware.wsgi import WSGIMiddleware
from admin_main import app as flask_app
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from cosine_search.top_results import GetTopNResults
from db.mongo_connector import MongoConnector
from db.consts import DB_SERVICES, get_lat_lon

EXAMPLE_RESULTS = [1, 1, 0, 1, 1,
                   0, 1, 1, 1, 0,
                   0, 0, 0, 0, 0,
                   0, 0, 0, 0, 1,
                   0, 0, 0, 1, 1,
                   1, 1, 0, 0, 1]

description = """
# POCAS SERVICE API
 * Can get all services in API
 * Post new services
 * Get Questionnaire results
## POCAS ADMIN PANEL: <a href="/admin">LINK</a>
"""
app = FastAPI(title="POCAS API",
              version="0.0.1",
              description=description
              )
security = HTTPBasic()


# TODO: get name from database
def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = b"chris"
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = b"duh"
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


class Service(BaseModel):
    name: str = Field(example='Test Service')
    phone: Optional[int] = Field(example=5559995555)
    address: Optional[str] = Field(example='1111 S 110th Ave.')
    general_topic: str = Field(example='Topic1')
    tags: List[str] = Field(example=['Tag1', 'Tag2'], default=[])
    city: Optional[str] = Field(example='Austin')
    state: Optional[str] = Field(example='TX')
    lat: Optional[float] = Field(example=72.34, default=None)
    long: Optional[float] = Field(example=34.01, default=None)
    zip_code: Optional[int] = Field(example=78724)
    web_site: Optional[str] = Field(example="http://www.example.com")


class FullServices(BaseModel):
    services: List[Service] = []
    num_of_services: int


@app.get('/services', response_model=FullServices)
async def get_services():
    """
    Get all Services for POCAS
    """
    m = MongoConnector(fsync=True)
    all_services = m.query_results(db=DB_SERVICES['db'], collection=DB_SERVICES['collection'],
                                   query={}, exclude={'loc': 0})
    for r in all_services:
        r['id'] = str(r['_id'])
        r.pop('_id', None)
    num_docs = len(all_services)
    if num_docs > 0:
        response = {'services': all_services, 'num_of_services': num_docs}
        return response
    else:
        raise HTTPException(status_code=404, detail="Services not found")


@app.post('/services', dependencies=[Depends(get_current_username)])
async def post_new_service(service: Service):
    """
    Upload Service to MongoDB
    """
    m = MongoConnector()
    payload = service.dict()
    payload = get_lat_lon(payload)
    mongo_id = m.upload_results(db=DB_SERVICES['db'],
                                collection=DB_SERVICES['collection'], data=[payload])
    return {'id': str(mongo_id[0])}


@app.post('/top_n', dependencies=[Depends(get_current_username)])
async def get_top_results(top_n: int, dob: int, address: str, answers: List[int] = EXAMPLE_RESULTS):
    """
    Send questionnaire and get Top N results
    """
    try:
        assert len(answers) == 30
        gtr = GetTopNResults(top_n=top_n, dob=dob, answers=answers, address=address)
        top_services, user_loc = gtr.get_top_results()
        for r in top_services:
            r['id'] = str(r['_id'])
            r.pop('_id', None)
        assert len(top_services) <= int(top_n)
        return {'services': top_services, 'num_of_services': len(top_services), 'user_loc': user_loc}
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=404, detail="Results not found")

app.mount("/", WSGIMiddleware(flask_app))
