"""Create Text Index on Name for Services"""
from pymongo import TEXT

from db.mongo_connector import MongoConnector
from db.consts import DB_SERVICES


m = MongoConnector()
services = m.client[DB_SERVICES["db"]][DB_SERVICES["collection"]]
services.create_index([("name", TEXT)], default_language="english")
