from db.mongo_connector import MongoConnector
import pandas as pd
import numpy as np
import googlemaps
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import os

AGE_MAPPER = {''}


class GetTopNResults:
    def __init__(self, top_n, dob, answers, address):
        self.top_n = top_n
        self.address = address
        self.dob = datetime.strptime(dob, '%m%d%Y')
        self.answers = answers
        self.lat = None
        self.lon = None

    def get_lat_lon(self):
        if os.getenv('GOOGLE_KEY') is None:
            raise Exception('Could not find Google Key! Set it in keys.env!')
        gmaps = googlemaps.Client(key=os.getenv('GOOGLE_KEY'))
        address = gmaps.geocode(self.address)
        self.lat = address[0]['geometry']['location']['lat']
        self.lon = address[0]['geometry']['location']['lng']

    def get_age(self):
        pass

    def map_answers_tags(self):
        a = self.answers
        return None

    def get_top_results(self):
        self.get_lat_lon()
        self.get_age()
        tags = self.map_answers_tags()
        m = MongoConnector()
        top_results = m.query_results(db='results', collection='services', query={'tags': tags})
        # run cosine similiarty and euclidean distance, get top n, normalize lat/lon

        return top_results
