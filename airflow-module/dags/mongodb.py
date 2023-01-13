import os
from pymongo import MongoClient


class MongoConnector:
    """
    General MongoDB Connector
    """

    def __init__(self, fsync=False):
        self.__host = os.getenv("MONGO_HOST", "0.0.0.0")
        self.__port = os.getenv("MONGO_PORT", "27017")
        self.__pass = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
        self.__user = os.getenv("MONGO_INITDB_ROOT_USERNAME")

        uri = f"mongodb://{self.__user}:{self.__pass}@{self.__host}:{self.__port}"
        self.client = MongoClient(uri, fsync=fsync)
