from db.mongo_connector import MongoConnector
import googlemaps
from datetime import datetime
import os
import logging
from db.consts import DB_SERVICES
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

AGE_MAPPER = {''}

ANSWERS_MAPPER = {''}
logging.basicConfig(level=logging.INFO)


class GetTopNResults:
    def __init__(self, top_n, dob, answers, address):
        self.top_n = top_n
        self.address = address
        self.dob = datetime.strptime(str(dob), '%m%d%Y')
        self.answers = answers
        self.lat = None
        self.lon = None
        self.age = self.get_age()

    def get_lat_lon(self):
        """
        Get Lat/Lon of User address from Google GeoCode API
        """
        if os.getenv('GOOGLE_KEY') is None:
            raise Exception('Could not find Google Key! Set it in keys.env!')
        gmaps = googlemaps.Client(key=os.getenv('GOOGLE_KEY'))
        address = gmaps.geocode(self.address)
        self.lat = address[0]['geometry']['location']['lat']
        self.lon = address[0]['geometry']['location']['lng']

    @staticmethod
    def log():
        return logging.getLogger('top_n_results')

    def get_age(self):
        """
        Get Age in Years
        :return: int
        """
        today = datetime.today()
        years = today.year - self.dob.year
        if today.month < self.dob.month or (today.month == self.dob.month and today.day < self.dob.day):
            years -= 1
        return years

    def map_answers_tags(self):
        """
        Map Questionairre to Mapper

        :return: Array of Tags Matched
        """
        a = self.answers
        return ['Public Benefits']

    def get_top_results(self):
        """
        Return Top Services

        :return:
        """
        self.get_lat_lon()
        tags = self.map_answers_tags()
        m = MongoConnector()
        top_results = m.query_results(db=DB_SERVICES['db'], collection=DB_SERVICES['collection'],
                                      query={'tags': {'$in': tags}},
                                      exclude={'loc': 0})
        self.log().info(top_results)
        self.log().info(self.__dict__)
        # run cosine similiarty and euclidean distance, get top n, normalize lat/lon
        for t in top_results:
            t['pocas_score'] = 0.99
        return top_results
