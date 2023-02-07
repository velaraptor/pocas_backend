"""FastAPI service"""
import datetime

# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611, R0903, W1309

import os
import io
import secrets
import uuid
import logging
from typing import Optional, List
from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    status,
    APIRouter,
    Request,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import StreamingResponse
from fastapi_limiterx import FastAPILimiter
from fastapi_limiterx.depends import RateLimiter
from fastapi_paginate import Page, add_pagination
from fastapi_paginate.ext.motor import paginate
import aioredis
from cosine_search.top_results import GetTopNResults
from db.mongo_connector import MongoConnector, MongoConnectorAsync
from db.consts import DB_SERVICES, get_lat_lon, EXAMPLE_RESULTS
from db.neo import BaseNeo
from models import (
    PDFResponse,
    RadiusZone,
    Service,
    FullServices,
    Disconnected,
    TopNResults,
    QuestionOut,
    D3Response,
    ServiceOut,
)
from mongo_utils import send_user_data, send_ip_address_mongo
from pdf_gen import generate_pdf

REDIS_NAME = "pocas_redis"
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MHP_API")
mongo_client = MongoConnectorAsync().client


@app.on_event("startup")
async def startup():
    """Redis Startup for FASTAPI Limiter"""
    redis = await aioredis.from_url(f"redis://{REDIS_NAME}", port=6379)
    await FastAPILimiter.init(redis)


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
            detail="Incorrect user or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get(
    "/api/v1/services",
    response_model=FullServices,
    dependencies=[Depends(RateLimiter(times=50, seconds=5))],
)
async def get_services(tag: Optional[str] = None):
    """
    Get all Services for POCAS
    """
    m = MongoConnectorAsync()
    query = {}
    if tag:
        query = {
            "$or": [
                {"tags": {"$in": [tag]}},
                {"general_topic": {"$in": [tag]}},
            ],
        }
    results = await m.query_results_api(
        db="results", collection="services", query=query
    )
    num_docs = len(results)
    if num_docs > 0:
        response = {"services": results, "num_of_services": num_docs}
        return response
    raise HTTPException(status_code=404, detail="Services not found")


@app.get(
    "/api/v1/services2",
    response_model=Page[ServiceOut],
    dependencies=[Depends(RateLimiter(times=50, seconds=5))],
)
async def get_services2():
    """
    Get all Services for POCAS Pagnation
    """
    return await paginate(mongo_client.results.services)


@app.get(
    "/api/v1/questions",
    response_model=Page[QuestionOut],
    dependencies=[Depends(RateLimiter(times=50, seconds=5))],
)
async def get_questions():
    """
    Get all Questions for POCAS
    """
    return await paginate(mongo_client.results.questions)


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
    m = MongoConnectorAsync()
    payload = service.dict()
    payload = get_lat_lon(payload)
    mongo_id = await m.upload_results(
        db=DB_SERVICES["db"], collection=DB_SERVICES["collection"], data=[payload]
    )
    return {"id": str(mongo_id[0])}


@app.post(
    "/api/v1/radius_check",
    dependencies=[
        Depends(get_current_username),
        Depends(RateLimiter(times=20, seconds=10)),
    ],
    response_model=RadiusZone,
)
async def check_zone(address: str):
    """Check if User is within zone of results"""
    gtr = GetTopNResults(top_n=1, dob="03011900", answers=[], address=address)
    gtr.get_lat_lon()
    check = gtr.find_radius()
    return {"radius_status": check}


@app.delete(
    "/api/v1/top_n/service/{_id}/{service_id}",
    dependencies=[
        Depends(get_current_username),
    ],
)
async def delete_service(_id: str, service_id: str):
    """Delete Service Recommended from MHP. Used when user deletes a card on frontend UI"""
    m = MongoConnector()
    db = "platform"
    collection = "user_data"
    if not _id or _id == "None":
        raise HTTPException(
            status_code=404, detail="Result _id cannot be None. No data found!"
        )
    try:
        c = m.client[db][collection]
        c.update_one({"name": _id}, {"$pull": {"top_services": service_id}})
        return {"status": True}
    except Exception as exc:
        logger.warning(exc)
        raise HTTPException(status_code=500, detail="Could not delete") from exc


@app.post(
    "/api/v1/top_n",
    dependencies=[
        Depends(get_current_username),
        Depends(RateLimiter(times=20, seconds=10)),
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
        m = MongoConnectorAsync()
        len_quest = await m.query_results_api(
            db="results", collection="questions", query={}
        )
        assert len(answers) == len(len_quest)
        gtr = GetTopNResults(top_n=top_n, dob=dob, answers=answers, address=address)
        top_services, user_loc = gtr.get_top_results()
        for r in top_services:
            r["id"] = str(r["_id"])
            r.pop("_id", None)
        assert len(top_services) <= int(top_n)
        result_id = uuid.uuid4().hex
        send_user_data(dob, address, answers, top_services, result_id)
        ip_data = {
            "ip_address": request.client.host,
            "endpoint": "top_n",
            "date": datetime.datetime.now(),
            "name": result_id,
        }
        if user_name:
            ip_data["ip_address"] = user_name
        send_ip_address_mongo([ip_data])
        return {
            "services": top_services,
            "num_of_services": len(top_services),
            "user_loc": user_loc,
            "name": result_id,
        }
    except Exception as exc:
        logger.warning(exc)
        raise HTTPException(status_code=404, detail="Results not found") from exc


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
    m = MongoConnectorAsync()
    zip_code_group = await m.aggregate(
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
    m = MongoConnectorAsync()
    query = {"zip_code": int(zip_code)}

    if start:
        date_query = {"$gte": start, "$lt": end}
        query["time"] = date_query

    results = await m.query_results_api(
        db="platform", collection="user_data", query=query
    )
    return results


@app.get(
    "/api/v1/alarms/disconnected",
    response_model=Disconnected,
    dependencies=[Depends(get_current_username)],
    tags=["alarms"],
)
async def check_disconnected():
    """Check Disconnected Services from Questions"""
    neo = BaseNeo()
    return neo.response_disconnected()


@app.get(
    "/api/v1/alarms/disconnected/network",
    response_model=D3Response,
    dependencies=[Depends(get_current_username)],
    tags=["alarms"],
)
async def get_network():
    """Get Neo4j Network in d3 JSON format"""
    neo = BaseNeo()
    neo.get_network()
    return neo.d3_response


add_pagination(app)
