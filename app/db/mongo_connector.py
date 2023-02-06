"""Default Mongo Connector to Read/Upload"""

import os
import logging
from pymongo import MongoClient, GEOSPHERE
import motor.motor_asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MongoConnector")
# pylint: disable=W0236


class MongoConnector:
    """
    General MongoDB Connector
    """

    def __init__(self, fsync=False):
        self.__host = os.getenv("MONGO_HOST", "0.0.0.0")
        self.__port = os.getenv("MONGO_PORT", "27017")
        self.__pass = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
        self.__user = os.getenv("MONGO_INITDB_ROOT_USERNAME")

        self._uri = f"mongodb://{self.__user}:{self.__pass}@{self.__host}:{self.__port}"
        self.client = MongoClient(self._uri, fsync=fsync)

    def aggregate(self, db, collection, query):
        """
        Use Pymongo Aggregate
        :param db: database to look at
        :type db: str
        :param collection: collection to look at
        :type collection: str
        :param query: query to run on collection
        :type query: dict
        :return: list[dict]
        """
        db = self.client[db]
        c = db[collection]

        pipeline = [
            query,
        ]
        results = c.aggregate(pipeline)
        agg_results = []
        for r in results:
            z = r
            z["id"] = str(z["_id"])
            z.pop("_id", None)
            agg_results.append(z)
        return agg_results

    def query_results_api(self, db, collection, query, exclude=None):
        """
        Safe Mongo Query for FastAPI response.

        The FastAPI response does not allow a field with `_id`. This changes it to 'id'.
        """
        results = self.query_results(db, collection, query, exclude)
        for r in results:
            r["id"] = str(r["_id"])
            r.pop("_id", None)
        return results

    def query_results(self, db, collection, query, exclude=None):
        """
        Query Mongo DB with database, collection and query

        :param db: database to look at
        :type db: str
        :param collection: collection to look at
        :type collection: str
        :param query: query to run on collection
        :type query: dict
        :param exclude: fields to exclude
        :return: list[dict]
        """
        if exclude is None:
            exclude = {}
        db = self.client[db]
        c = db[collection]
        results = []
        for c in c.find(query, exclude):
            results.append(c)
        return results

    @staticmethod
    def check_duplicates(c, data, key):
        """Check Duplicates in Collection"""
        results = []
        for d in c.find({key: data[key]}):
            results.append(d)
        if len(results) > 0:
            logger.info("Found Duplicates!")
            return None
        return data

    def upload_results(self, db, collection, data, geo_index=False, key="name"):
        """
        Upload Results to database, collection with data as a list of dictionaries

        :param db: database to look at
        :type db: str
        :param collection: collection to look at
        :type collection: str
        :param data: data to insert into mongodb
        :type data: list[dict]
        :param geo_index: create geo_index
        :return: list of meta ids of inserted documents
        :param key: key to check for duplicates
        """
        db = self.client[db]
        c = db[collection]
        if geo_index:
            c.create_index([("loc", GEOSPHERE)])
        data_temp = []
        for d in data:
            duplicate_check = self.check_duplicates(c, d, key)
            if duplicate_check:
                data_temp.append(duplicate_check)
        if len(data_temp) > 0:
            result = c.insert_many(data_temp)
            return result.inserted_ids
        return ["Duplicate!"]


class MongoConnectorAsync(MongoConnector):
    """
    General MongoDB Connector
    """

    def __init__(self, fsync=False):
        super().__init__(fsync=fsync)
        self.client = motor.motor_asyncio.AsyncIOMotorClient(self._uri, fsync=fsync)

    @staticmethod
    def clean_id(document):
        """Clean Id"""
        document = dict(document)
        document["id"] = str(document["_id"])
        document.pop("_id")
        return document

    async def aggregate(self, db, collection, query):
        """
        Use Pymongo Aggregate
        :param db: database to look at
        :type db: str
        :param collection: collection to look at
        :type collection: str
        :param query: query to run on collection
        :type query: dict
        :return: list[dict]
        """
        db = self.client[db]
        c = db[collection]

        pipeline = [
            query,
        ]
        documents = c.aggregate(pipeline)
        results = []
        async for doc in documents:
            results.append(self.clean_id(doc))
        return results

    async def query_results_api(self, db, collection, query, exclude=None):
        """
        Safe Mongo Query for FastAPI response.

        The FastAPI response does not allow a field with `_id`. This changes it to 'id'.
        """
        documents = await self.query_results(db, collection, query, exclude)
        results = []
        for doc in documents:
            results.append(self.clean_id(doc))
        return results

    async def query_results(self, db, collection, query, exclude=None):
        """
        Query Mongo DB with database, collection and query

        :param db: database to look at
        :type db: str
        :param collection: collection to look at
        :type collection: str
        :param query: query to run on collection
        :type query: dict
        :param exclude: fields to exclude
        :return: list[dict]
        """
        if exclude is None:
            exclude = {}
        db = self.client[db]
        c = db[collection]
        results = await c.find(query, exclude).to_list(length=None)
        return results

    @staticmethod
    async def check_duplicates(c, data, key):
        """Check Duplicates in Collection"""
        results = await c.find({key: data[key]}).to_list(length=None)
        if len(results) > 0:
            logger.info("Found Duplicates!")
            return None
        return data

    async def upload_results(self, db, collection, data, geo_index=False, key="name"):
        """
        Upload Results to database, collection with data as a list of dictionaries

        :param db: database to look at
        :type db: str
        :param collection: collection to look at
        :type collection: str
        :param data: data to insert into mongodb
        :type data: list[dict]
        :param geo_index: create geo_index
        :return: list of meta ids of inserted documents
        :param key: key to check for duplicates
        """
        db = self.client[db]
        c = db[collection]
        if geo_index:
            await c.create_index([("loc", GEOSPHERE)])
        data_temp = []
        for d in data:
            duplicate_check = await self.check_duplicates(c, d, key)
            if duplicate_check:
                data_temp.append(duplicate_check)
        if len(data_temp) > 0:
            result = await c.insert_many(data_temp)
            return result.inserted_ids
        return ["Duplicate!"]
