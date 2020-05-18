from pymongo import MongoClient
import os


class MongoConnector:
    def __init__(self):
        self.host = os.getenv('MONGO_HOST')
        self.port = os.getenv('MONGO_PORT')
        self.__pass = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
        self.__user = os.getenv('MONGO_INITDB_ROOT_USERNAME')
        uri = "mongodb://%s:%s@%s:%s" % (self.__user, self.__pass, self.host, self.port)
        self.client = MongoClient(uri)

    def query_results(self, db, collection, query):
        db = self.client[db]
        c = db[collection]
        results = []
        for c in c.find(query):
            results.append(c)
        return results

    def upload_results(self, db, collection, data):
        db = self.client[db]
        c = db[collection]
        result = c.insert_many(data)
        return result.inserted_ids
