"""Generic Top Services Class"""
import urllib.parse
import operator
from frontend.setup_logging import logger


class Service:
    """One Service Object"""

    name = None
    phone = None
    address = None
    general_topic = None
    tags = None
    city = None
    state = None
    lat = None
    lon = None
    zip_code = None
    web_site = None
    days = None
    hours = None
    id = None
    pocas_score = 0.5
    sms_payload = None

    def __init__(self, service):
        for key, value in service.items():
            setattr(self, key, value)
        logger.debug(f"{self.name}: {self.pocas_score}")
        if not self.pocas_score:
            self.pocas_score = 0.5
        self.remove_tag_duplicate()

    def __eq__(self, other):
        return self.id == other.id and self.name == other.name

    def __hash__(self):
        return hash(("id", self.id, "name", self.name))

    def serialize(self):
        """Serialize Service object"""
        return self.__dict__

    def remove_tag_duplicate(self):
        """Remove Tag Duplciate if General Topic"""
        if self.general_topic in self.tags:
            self.tags = [tag for tag in self.tags if tag != self.general_topic]

    def encode_service(self):
        """Encode Service for SMS"""
        body = self.name + "\n"
        if self.phone:
            body = body + f"Phone: {self.phone}" + "\n"
        if self.address:
            body = body + f"Address: {self.address}" + "\n"
        if self.days:
            body = body + f"Days: {self.days}" + "\n"
        if self.hours:
            body = body + f"Hours: {self.hours}" + "\n"
        if self.web_site:
            body = body + f"Web Site: {self.web_site}" + "\n"
        body = body + "Sent via MHP Portal (https://mhpportal.app)"
        safe_body = urllib.parse.quote(body)
        self.sms_payload = safe_body


class Services:
    """Services object for FrontEnd"""

    services = None
    num_of_services = None
    user_loc = None
    name = None

    def __init__(self, payload):
        self.services = []
        logger.debug(f"Initial Services: {self.services}")
        for key, value in payload.items():
            if key == "services":
                for service in value:
                    self.services.append(Service(service))
            else:
                setattr(self, key, value)
        self.services = list(set(self.services))
        logger.info(f"Length of Services at init: {len(self.services)}")

    def export(self):
        """Export dict to be read"""
        payload = self.__dict__
        payload["services"] = [s.serialize() for s in self.services]
        return payload

    def sort(self, key="general_topic", desc=False):
        """Sort by key in services"""
        self.services = sorted(
            self.services, key=operator.attrgetter(key), reverse=desc
        )
        logger.debug(f"Length of Services at sort: {len(self.services)}")

    def filter(self, filter_val):
        """Filter based on filter Value for tags and general topic"""
        services_g = list(
            filter(lambda x: x.general_topic == filter_val, self.services)
        )
        services_t = [
            x
            for x in self.services
            if filter_val in x.tags and filter_val != x.general_topic
        ]
        services = services_t + services_g
        self.services = services
        self.num_of_services = len(services)
        self.encode_services()

    def encode_services(self):
        """Encode ALL Services for SMS by iterating over loop"""
        for s in self.services:
            s.encode_service()
