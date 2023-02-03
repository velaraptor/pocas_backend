"""Mongo Utils"""
import datetime
import logging
from db.mongo_connector import MongoConnector


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mongo_utils")


def send_user_data(dob, address, answers, services, result_id):
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
                "name": result_id,
            }
        ]
        m = MongoConnector()
        db = "platform"
        collection = "user_data"
        m.upload_results(db, collection, data)
    except Exception as e:
        logger.warning("Send User data did not send!")
        logger.warning(dob)
        logger.warning(str(e))


def send_ip_address_mongo(data):
    """Send IP address for IP Analytics"""
    try:
        m = MongoConnector()
        db = "analytics"
        collection = "ip_hits"
        m.upload_results(db, collection, data)
    except Exception as e:
        logger.warning(str(e))
