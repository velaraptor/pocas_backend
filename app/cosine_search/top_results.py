from datetime import datetime
import os
import logging
import traceback

import googlemaps

from db.consts import DB_SERVICES
from db.mongo_connector import MongoConnector

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import Normalizer

AGE_MAPPER = {
    'Elder': [51, 120],
    'Adult': [36, 50],
    'Young Adult': [21, 35],
    'Adolescent': [0, 20]}

ANSWERS_MAPPER = {''}

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] %(name)s [%(levelname)s]: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class GetTopNResults:
    def __init__(self, top_n, dob, answers, address):
        self.top_n = top_n if top_n != 0 else 1
        self.__address = address
        self.dob = datetime.strptime(str(dob), '%m%d%Y')
        self.answers = answers
        self.lat = None
        self.lon = None
        self.age = self.get_age()
        self.tags = []

    def get_lat_lon(self):
        """
        Get Lat/Lon of User address from Google GeoCode API
        """
        if os.getenv('GOOGLE_KEY') is None:
            raise Exception('Could not find Google Key! Set it in keys.env!')
        gmaps = googlemaps.Client(key=os.getenv('GOOGLE_KEY'))
        address = gmaps.geocode(self.__address)
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
        Map Questionnaire to Mapper

        :return: Array of Tags Matched
        """
        answers = self.answers

        # TODO: map with tags
        age_df = pd.DataFrame(AGE_MAPPER)
        vals = np.abs(np.sum(age_df - self.age))

        age_tags = vals[vals == np.min(vals)].index.values[0]
        answer_tags = ['Domestic Violence', 'Legal Services']
        return answer_tags + [age_tags]

    def run_similarity(self, results):
        """
        run cosine similarity and euclidean distance, get top n, normalize lat/lon
        :param results:
        :return:
        """

        df_results = pd.DataFrame(results)
        dummies_tags = pd.get_dummies(df_results.tags.apply(pd.Series).stack()).sum(level=0)
        matrix = pd.concat([df_results[['lat', 'lon']], dummies_tags], axis=1)
        matrix_val = matrix.values
        tags_unique = dummies_tags.columns.values
        overall_length = len(tags_unique)

        empty_user_tags = pd.DataFrame([np.zeros(overall_length)],
                                       columns=tags_unique)
        for tag in self.tags:
            if tag in empty_user_tags:
                empty_user_tags[tag] = 1

        user_vector = [self.lat, self.lon]
        user_vector = np.concatenate((user_vector, empty_user_tags.values[0]))

        sim_matrix = np.vstack((matrix_val, user_vector))

        weights = np.concatenate(([0.0005, 0.0005], np.ones(overall_length) * 1.25))
        sim_matrix = Normalizer().transform(sim_matrix * weights)
        sim_values = cosine_similarity(sim_matrix)
        self.log().debug(sim_values)
        sim_vals = sim_values[len(df_results)][:len(df_results)]

        df_results['pocas_score'] = sim_vals
        df_results = df_results.sort_values('pocas_score', ascending=False)
        final_results = df_results[:int(self.top_n)]
        final_results = final_results.to_dict(orient='records')
        return final_results

    def get_top_results(self):
        """
        Return Top Services

        :return:
        """
        self.get_lat_lon()
        self.tags = self.map_answers_tags()
        m = MongoConnector()
        top_results = m.query_results(db=DB_SERVICES['db'], collection=DB_SERVICES['collection'],
                                      query={'tags': {'$in': self.tags}},
                                      exclude={'loc': 0})
        self.log().debug(self.__dict__)
        try:
            final_results = self.run_similarity(top_results)
        except Exception:
            traceback.print_exc()
            self.log().warning('Could not run cosine sim, reverting to mongo query results')
            final_results = top_results
        self.log().info(final_results)

        return final_results
