from pymongo import MongoClient, GEOSPHERE
import os


class MongoConnector:
    """
    General MongoDB Connector
    """
    def __init__(self):
        self.__host = os.getenv('MONGO_HOST')
        self.__port = os.getenv('MONGO_PORT')
        self.__pass = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
        self.__user = os.getenv('MONGO_INITDB_ROOT_USERNAME')

        uri = "mongodb://%s:%s@%s:%s" % (self.__user, self.__pass, self.__host, self.__port)
        self.client = MongoClient(uri)

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

    def upload_results(self, db, collection, data,  geo_index=False):
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
        """
        db = self.client[db]
        c = db[collection]
        if geo_index:
            c.create_index([("loc", GEOSPHERE)])
        result = c.insert_many(data)
        return result.inserted_ids
