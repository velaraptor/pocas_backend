"""FastAPI service"""
import datetime

# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611, R0903, W1309

import os
import io
import secrets
import uuid
from typing import Optional, List
from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    status,
    APIRouter,
    Request,
    Response,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import StreamingResponse
from fastapi_limiterx import FastAPILimiter
from fastapi_limiterx.depends import RateLimiter
import aioredis
from pydantic import BaseModel, Field
from neo4j import GraphDatabase
from cosine_search.top_results import GetTopNResults, get_all_services
from db.mongo_connector import MongoConnector
from db.consts import DB_SERVICES, get_lat_lon
from pdf_gen import generate_pdf

EXAMPLE_RESULTS = [
    1,
    1,
    0,
    1,
    1,
    0,
    1,
    1,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    1,
    1,
    1,
    1,
    0,
    0,
    0,
]

description = """
# POCAS SERVICE API
 * Can get all services in API
 * Post new services
 * Get Questionnaire results
## POCAS ADMIN PANEL: <a href="/admin">LINK</a>
"""
app = FastAPI(
    title="POCAS API",
    version="0.0.1",
    description=description,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)
security = HTTPBasic()
temp = APIRouter()
app.include_router(temp, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    """Redis Startup for FASTAPI Limiter"""
    REDIS_NAME = "pocas_redis"
    redis = await aioredis.from_url(f"redis://{REDIS_NAME}", port=6379)
    await FastAPILimiter.init(redis)


def send_ip_address_mongo(data):
    """Send IP address for IP Analytics"""
    try:
        m = MongoConnector()
        db = "analytics"
        collection = "ip_hits"
        m.upload_results(db, collection, data)
    except Exception as e:
        print(str(e))


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    """Get Current Username and compare for BasicAuth"""
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = bytes(os.getenv("API_USER"), "utf-8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = bytes(os.getenv("API_PASS"), "utf-8")
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
    """Base Model for Service"""

    name: str = Field(example="Test Service")
    phone: Optional[int] = Field(example=5559995555)
    address: Optional[str] = Field(example="1111 S 110th Ave.")
    general_topic: str = Field(example="Topic1")
    tags: List[str] = Field(example=["Tag1", "Tag2"], default=[])
    city: Optional[str] = Field(example="Austin")
    state: Optional[str] = Field(example="TX")
    lat: Optional[float] = Field(example=72.34, default=None)
    lon: Optional[float] = Field(example=34.01, default=None)
    zip_code: Optional[int] = Field(example=78724)
    web_site: Optional[str] = Field(example="http://www.example.com")
    days: Optional[str]
    hours: Optional[str]
    id: Optional[str]


class FullServices(BaseModel):
    """Full Services Model"""

    services: List[Service]
    num_of_services: int


class Question(BaseModel):
    """Questions Model"""

    id: int
    question: str
    tags: List[str]
    main_tag: Optional[str]


class QuestionList(BaseModel):
    """Questions Model"""

    questions: List[Question]


class UserLocation(BaseModel):
    """User Location Model"""

    lat: float
    lon: float


class TopNResults(BaseModel):
    """Top Results Model"""

    services: List[Service]
    num_of_services: int
    user_loc: UserLocation


class RadiusZone(BaseModel):
    """Radius Model"""

    radius_status: bool


@app.get(
    "/api/v1/services",
    response_model=FullServices,
    dependencies=[Depends(RateLimiter(times=50, seconds=5))],
)
async def get_services():
    """
    Get all Services for POCAS
    """
    all_services = get_all_services()
    num_docs = len(all_services)
    if num_docs > 0:
        response = {"services": all_services, "num_of_services": num_docs}
        return response
    raise HTTPException(status_code=404, detail="Services not found")


@app.get(
    "/api/v1/questions",
    response_model=QuestionList,
    dependencies=[Depends(RateLimiter(times=50, seconds=5))],
)
async def get_questions():
    """
    Get all Questions for POCAS
    """
    m = MongoConnector()
    questions = GetTopNResults(1, 1205970, None, None).get_questions(m)
    num_docs = len(questions)
    if num_docs > 0:
        response = {"questions": questions}
        return response
    raise HTTPException(status_code=404, detail="Questions not found")


@app.post(
    "/api/v1/services",
    dependencies=[
        Depends(get_current_username),
        Depends(RateLimiter(times=1, seconds=5)),
    ],
)
async def post_new_service(service: Service):
    """
    Upload Service to MongoDB
    """
    # https://github.com/uriyyo/fastapi-pagination/blob/main/fastapi_pagination/ext/pymongo.py
    m = MongoConnector()
    payload = service.dict()
    payload = get_lat_lon(payload)
    mongo_id = m.upload_results(
        db=DB_SERVICES["db"], collection=DB_SERVICES["collection"], data=[payload]
    )
    return {"id": str(mongo_id[0])}


def send_user_data(dob, address, answers, services):
    """Send data for Platform Analytics"""
    try:
        service_ids = [service["id"] for service in services]

        data = [
            {
                "dob": int(str(dob)[-4:]),
                "zip_code": int(address),
                "answers": answers,
                "top_services": service_ids,
                "time": datetime.datetime.now(),
                "name": uuid.uuid4().hex,
            }
        ]
        m = MongoConnector()
        db = "platform"
        collection = "user_data"
        m.upload_results(db, collection, data)
    except Exception as e:
        print("Send User data did not send!")
        print(dob)
        print(str(e))


@app.post(
    "/api/v1/radius_check",
    dependencies=[
        Depends(get_current_username),
        Depends(RateLimiter(times=10, seconds=60)),
    ],
    response_model=RadiusZone,
)
async def check_zone(address: str):
    """Check if User is within zone of results"""
    gtr = GetTopNResults(top_n=1, dob="03011900", answers=[], address=address)
    gtr.get_lat_lon()
    check = gtr.find_radius()
    return {"radius_status": check}


@app.post(
    "/api/v1/top_n",
    dependencies=[
        Depends(get_current_username),
        Depends(RateLimiter(times=10, seconds=60)),
    ],
    response_model=TopNResults,
)
async def get_top_results(  # pylint: disable=dangerous-default-value
    request: Request,
    top_n: int,
    dob: int,
    address: str,
    user_name: str = None,
    answers: List[int] = EXAMPLE_RESULTS,
):
    """
    Send questionnaire and get Top N results
    """
    try:
        len_quest = await get_questions()
        assert len(answers) == len(len_quest["questions"])
        gtr = GetTopNResults(top_n=top_n, dob=dob, answers=answers, address=address)
        top_services, user_loc = gtr.get_top_results()
        for r in top_services:
            r["id"] = str(r["_id"])
            r.pop("_id", None)
        assert len(top_services) <= int(top_n)
        send_user_data(dob, address, answers, top_services)
        ip_data = {
            "ip_address": request.client.host,
            "endpoint": "top_n",
            "date": datetime.datetime.now(),
            "name": uuid.uuid4().hex,
        }
        if user_name:
            ip_data["ip_address"] = user_name
        send_ip_address_mongo([ip_data])
        return {
            "services": top_services,
            "num_of_services": len(top_services),
            "user_loc": user_loc,
        }
    except Exception as exc:
        print(exc)
        raise HTTPException(status_code=404, detail="Results not found") from exc


class PDFResponse(Response):
    """Response Type for PDF"""

    media_type = "application/pdf"


@app.post(
    "/api/v1/pdf",
    dependencies=[Depends(get_current_username)],
    response_class=PDFResponse,
)
async def generate_pdf_get(services: List[Service]):
    """Generate PDF from Array of Services"""
    pdf = generate_pdf(services)
    return StreamingResponse(
        content=io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-disposition": f'inline; filename="results.pdf'},  # noqa: F541
    )


@app.get(
    "/api/v1/platform/zip_codes",
    dependencies=[Depends(get_current_username)],
    tags=["platform"],
)
async def get_zip_codes():
    """
    Get Group By of all Zip Codes in User Data
    """
    m = MongoConnector()
    zip_code_group = m.aggregate(
        db="platform",
        collection="user_data",
        query={
            "$group": {
                "_id": "$zip_code",
                "count": {"$sum": 1},
            }
        },
    )
    return zip_code_group


@app.get(
    "/api/v1/platform/data/{zip_code}",
    dependencies=[Depends(get_current_username)],
    tags=["platform"],
)
async def get_user_data(
    zip_code: int,
    start: Optional[datetime.datetime] = None,
    end: Optional[datetime.datetime] = None,
):
    """
    Get User Data with zip code and optional start-end time. Note time must be in following str format:

    `2022-11-16T19:00:44.173000`
    """
    # tie answers to tags
    m = MongoConnector()
    query = {"zip_code": int(zip_code)}

    if start:
        date_query = {"$gte": start, "$lt": end}
        query["time"] = date_query

    results = m.query_results_api(db="platform", collection="user_data", query=query)
    return results


class BaseNeo:
    """Base Neo4j API"""

    def __init__(self):
        self.__host = os.getenv("NEO_HOST", "0.0.0.0")
        self.__port = os.getenv("NEO_PORT", "7687")
        self.__user = os.getenv("NEO_USER", "neo4j")
        self.__pwd = os.getenv("NEO_PWD")
        self.driver = GraphDatabase.driver(
            f"bolt://{self.__host}:{self.__port}", auth=(self.__user, self.__pwd)
        )
        self.max_date = None

    def find_max_date(self):
        """Find Import Max Date"""

        with self.driver.session() as session:
            data = session.run(
                """
                MATCH (n:Import)
                RETURN MAX(n.date) as date
                """
            )
            self.max_date = data.data()[0]["date"]

    def run_services_disconnected(self):
        """Get Tags disconnected to Questions"""
        with self.driver.session() as session:
            data = session.run(
                """
                    MATCH (n:Services)-[:TAGGED]->(n1:Tags)
                WHERE NOT (n1)-[:TAGGED]-(:Questions)
                // Young Adult Resources is tied by Age Question
                      AND n1.name <> 'Young Adult Resources'
                      AND NOT (n)-[:TAGGED]-(n1)-[:TAGGED]-(:Questions)
                      AND n.date = n1.date = $max_date
                RETURN n.id as service_id, n.name as service, COLLECT(n1.name) as tags
                ORDER BY tags;
                """,
                max_date=self.max_date,
            )
            df = data.to_df().to_dict(orient="records")
            return df

    def run_tags_disconnected(self):
        """Get Services disconnected to Questions"""
        with self.driver.session() as session:
            data = session.run(
                """
                MATCH (n:Services)-[:TAGGED]->(n1:Tags)
                WHERE NOT (n1)-[:TAGGED]-(:Questions)
                // Young Adult Resources is tied by Age Question
                      AND n1.name <> 'Young Adult Resources'
                      AND n.date = n1.date = $max_date
                WITH n1.name as tags
                RETURN tags as name, COUNT(*) as value
                ORDER BY name;
                """,
                max_date=self.max_date,
            )
            tag = data.to_df().to_dict(orient="records")
            return tag

    def get_network(self):
        """
        Get network and in format for D3 Network Graph
        """
        with self.driver.session() as session:
            data = session.run(
                """
                MATCH p=(a)-[]->(b)
                WHERE LABELS(a) in [['Services'], ['Tags'], ['Questions']]
                AND LABELS(b) in [['Services'], ['Tags'], ['Questions']]
                AND a.date = b.date = $max_date
                WITH p unwind nodes(p) as n unwind relationships(p) as r
                WITH collect( distinct {id: ID( n), name: n.name, group: LABELS(n)[0] }) as nl,
                     collect( distinct {source: ID(startnode(r)), target: ID(endnode(r)) }) as rl
                RETURN {nodes: nl, links: rl} as payload
                """,
                max_date=self.max_date,
            )
            return data.data()[0]["payload"]


class ServiceNeo(BaseModel):
    """Disconnected Service Model"""

    service_id: str = Field(example=uuid.uuid4().hex)
    service: str = Field(example="Test Center Service")
    tags: List[str] = Field(example=["Tag1", "Tag2"])


class Stats(BaseModel):
    """Disconnected Stats Model"""

    tags: int
    services: int


class Tag(BaseModel):
    """Tags Disconnected"""

    name: str = Field(example="Tag1")
    value: int = Field(example=15)


class Disconnected(BaseModel):
    """Disconnected Services Model"""

    services: List[ServiceNeo]
    tags: List[Tag]
    stats: Stats


@app.get(
    "/api/v1/alarms/disconnected",
    response_model=Disconnected,
    dependencies=[Depends(get_current_username)],
    tags=["alarms"],
)
async def check_disconnected():
    """Check Disconnected Services from Questions"""
    neo = BaseNeo()
    neo.find_max_date()
    services = neo.run_services_disconnected()
    tags = neo.run_tags_disconnected()
    response = {
        "services": services,
        "tags": tags,
        "stats": {"tags": len(tags), "services": len(services)},
    }
    return response


@app.get(
    "/api/v1/alarms/disconnected/network",
    dependencies=[Depends(get_current_username)],
    tags=["alarms"],
)
async def get_network():
    """Check Neo4j Network"""
    neo = BaseNeo()
    neo.find_max_date()
    response = neo.get_network()
    return response
