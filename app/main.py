"""FastAPI service"""
import datetime

# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611, R0903, W1309

import os
import io
import secrets
import uuid
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, status, APIRouter, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import StreamingResponse
from fastapi_limiterx import FastAPILimiter
from fastapi_limiterx.depends import RateLimiter
import aioredis
from pydantic import BaseModel, Field
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


class FullServices(BaseModel):
    """Full Services Model"""

    services: List[Service]
    num_of_services: int


class UserLocation(BaseModel):
    """User Location Model"""

    lat: float
    lon: float


class TopNResults(BaseModel):
    """Top Results Model"""

    services: List[Service]
    num_of_services: int
    user_loc: UserLocation


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
    m = MongoConnector()
    payload = service.dict()
    payload = get_lat_lon(payload)
    mongo_id = m.upload_results(
        db=DB_SERVICES["db"], collection=DB_SERVICES["collection"], data=[payload]
    )
    return {"id": str(mongo_id[0])}


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
    answers: List[int] = EXAMPLE_RESULTS,
):
    """
    Send questionnaire and get Top N results
    """
    try:
        assert len(answers) == 29
        gtr = GetTopNResults(top_n=top_n, dob=dob, answers=answers, address=address)
        top_services, user_loc = gtr.get_top_results()
        for r in top_services:
            r["id"] = str(r["_id"])
            r.pop("_id", None)
        assert len(top_services) <= int(top_n)
        ip_data = {
            "ip_address": request.client.host,
            "endpoint": "top_n",
            "date": datetime.datetime.now(),
            "name": uuid.uuid4().hex,
        }
        send_ip_address_mongo([ip_data])
        return {
            "services": top_services,
            "num_of_services": len(top_services),
            "user_loc": user_loc,
        }
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Results not found") from exc


@app.post("/api/v1/pdf", dependencies=[Depends(get_current_username)])
async def generate_pdf_get(services: List[Service]):
    """Generate PDF from Array of Services"""
    pdf = generate_pdf(services)
    return StreamingResponse(
        content=io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-disposition": f'inline; filename="results.pdf'},  # noqa: F541
    )
