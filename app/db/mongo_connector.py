"""Default Mongo Connector to Read/Upload"""
import os
from pymongo import MongoClient, GEOSPHERE


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
            print("Found Duplicates!")
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
