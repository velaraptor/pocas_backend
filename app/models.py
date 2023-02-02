"""Fast API Models"""
# pylint: disable=R0903

import uuid
from typing import Optional, List
from fastapi import Response
from pydantic import BaseModel, Field


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
    name: str = Field(example=uuid.uuid4().hex)


class RadiusZone(BaseModel):
    """Radius Model"""

    radius_status: bool


class PDFResponse(Response):
    """Response Type for PDF"""

    media_type = "application/pdf"


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
    max_date: str


class Node(BaseModel):
    """Node Model"""

    name: str = Field(example="Node A")
    id: int = Field(example=3019)
    group: str = Field(example="Tag")


class Link(BaseModel):
    """Link Model"""

    source: int = Field(example=3019)
    target: int = Field(example=3020)


class D3Response(BaseModel):
    """D3 JSON MODEL"""

    nodes: List[Optional[Node]]
    links: List[Optional[Link]]
