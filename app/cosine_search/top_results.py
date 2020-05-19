from db.mongo_connector import MongoConnector
import googlemaps
from datetime import datetime
import os
import logging
import traceback

from db.consts import DB_SERVICES
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

AGE_MAPPER = {''}

ANSWERS_MAPPER = {''}

logging.basicConfig(level=logging.INFO)


class GetTopNResults:
    def __init__(self, top_n, dob, answers, address):
        self.top_n = top_n if top_n != 0 else 1
        self.address = address
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
        Map Questionnaire to Mapper

        :return: Array of Tags Matched
        """
        a = self.answers
        # TODO: map with age and tags 
        return ['Public Benefits']

    def run_similarity(self, results):
        """
        run cosine similarity and euclidean distance, get top n, normalize lat/lon
        :param results:
        :return:
        """

        df_results = pd.DataFrame(results)
        dummies_tags = pd.get_dummies(df_results.tags.apply(pd.Series).stack()).sum(level=0)
        dummies_general_topic = pd.get_dummies(df_results.general_topic)

        matrix = pd.concat([df_results[['lat', 'lon']], dummies_tags, dummies_general_topic], axis=1)
        matrix_val = matrix.values
        general_topic_unique = dummies_general_topic.columns.values
        tags_unique = dummies_tags.columns.values
        overall_length = len(general_topic_unique) + len(tags_unique)

        empty_user_tags = pd.DataFrame([np.zeros(overall_length)],
                                       columns=np.concatenate((general_topic_unique, tags_unique)))
        for tag in self.tags:
            empty_user_tags[tag] = 1

        user_vector = [self.lat, self.lon]
        user_vector = np.concatenate((user_vector, empty_user_tags.values[0]))

        sim_matrix = np.vstack((matrix_val, user_vector))
        sim_values = cosine_similarity(sim_matrix)
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
        self.log().info(self.__dict__)
        try:
            final_results = self.run_similarity(top_results)
        except Exception:
            traceback.print_exc()
            self.log().warning('Could not run cosine sim, reverting to mongo query results')
            final_results = top_results
        self.log().info(final_results)

        return final_results
