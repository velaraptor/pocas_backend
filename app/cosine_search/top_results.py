from datetime import datetime
import os
import logging
import traceback

import googlemaps
from collections import OrderedDict

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

# TODO: do this programatically
ALL_TAGS = ['Adolescent', 'Child Support', 'Disability', 'Domestic Violence',
       'Education', 'Elder', 'Employment', 'Family', 'Food and Nutrition',
       'Health Insurance', 'Housing', 'Indigent', 'LGBTQ', 'Legal Services',
       'Low Income', 'Mental Health', 'Public Benefits', 'Shelter',
       'Social Security', 'Special Education', 'Transportation',
       'Young Adult']

QUESTIONS = OrderedDict({
            'In the last year, have you worried that food would, run out before you got money to buy more?': ['Food and Nutrition', 'Family', 'Public Benefits'],
             'Is anyone scaring, threatening or hurting you or your children?': ['Domestic Violence', 'Shelter', 'Family'],
             'Every family has fights.  What are fights like in your home?': ['Domestic Violence', 'Family', 'Shelter'],
             'Do  you  ever  skip  or  cut  the  dose  of  a  medicine  because of cost?': ['Health Insurance', 'Low Income'],
             'Do you and your family have health insurance?  If not, have you applied for AHCCCS, KidsCare, ACA insurance or other benefits?': ['Health Insurance'],
             'Are you pregnant?  If so, have you spoken to anyone about WIC?': ['Family', 'Health Insurance', 'Public Benefits', 'Low Income'],
             'If you have applied for assistance and been denied, have you filed an appeal?': ['Pubic Benefits', 'Social Security', 'Low Income', 'Child Support'],
             'Are you working?': ['Employment', 'Public Benefits', 'Low Income'],
             'Do you always have enough food to eat?': ['Public Benefits', 'Food and Nutrition'],
             'Are you receiving benefits from programs such as Cash Assistance or Food Stamps?': ['Public Benefits', 'Food and Nutrition', 'Employment', 'Low Income'],
             'In the last year, have you worried that food would run out before you got money to buy more?': ['Public Benefits', 'Food and Nutrition', 'Employment', 'Low Income'],
             'Are you or anyone in your family >65, blind or disabled?': ['Social Security', 'Elder', 'Disability'],
             'Have you applied for SSI /SSDI benefits?': ['Social Security', 'Public Benefits'],
             'Do you have concerns/problems with your home?': ['Housing', 'Public Benefits', 'Shelter'],
             'Do you have any problems with your landlord?': ['Housing', 'Public Benefits'],
             'Do you have mold, mice or roaches in your home?': ['Housing', 'Public Benefits'],
             'Was your home built before 1978?': ['Housing', 'Public Benefits'],
             'Do you have peeling/chipping paint in your home?': ['Housing', 'Public Benefits'],
             'Do you have smoke and CO2 detectors?': ['Housing', 'Public Benefits'],
             'How are your children doing in school?': ['Education', 'Family', 'Adolescent', 'Young Adult'],
             'Are they failing or struggling in any classes?': ['Education', 'Family', 'Adolescent'],
             'Do they have problems getting along with other children or teachers? ': ['Education', 'Family', 'Adolescent', 'Mental Health'],
             'How often do they miss school?': ['Education', 'Family', 'Adolescent'],
             'Does your child have a disability?': ['Education', 'Family', 'Adolescent', 'Disability', 'Special Education'],
             'Has your child been evaluated for special education services?': ['Education', 'Family', 'Adolescent', 'Disability', 'Special Education'],
             'Does your child have an Individual Education Program (IEP) or Section 504 plan?': ['Education', 'Family', 'Adolescent', 'Disability', 'Special Education'],
             'Would you like to discuss any legal problems with an attorney at no cost': ['Legal Services', 'Indigent'],
             'Identify as LBTQ?': ['LGBTQ'],
             'Identify as Indigent?': ['Indigent'],
             'Need transportation': ['Transportation']
             })


QUESTIONS_LIST = list(QUESTIONS)


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
        age_df = pd.DataFrame(AGE_MAPPER)
        vals = np.abs(np.sum(age_df.values - self.age))

        age_tags = vals[vals == np.min(vals)].index.values[0]

        # find tags from questions

        # make binary to boolean
        bool_answers = list(map(bool, answers))
        # filter questions that were answered yes
        answers_to_use = np.array(QUESTIONS_LIST)[bool_answers]

        # add all tags from yes answered questions
        tags_user = []
        for answer in answers_to_use:
            tags_user = tags_user + QUESTIONS[answer]

        # add question and age tags
        answer_tags = tags_user + [age_tags]
        # remove dups
        answer_tags = list(set(answer_tags))
        return answer_tags

    def run_similarity(self, results):
        """
        run cosine similarity and euclidean distance, get top n, normalize lat/lon
        :param results:
        :return:
        """

        df_results = pd.DataFrame(results)
        df_results = df_results.drop_duplicates(subset=['name'])
        df_results['tags'] = df_results.apply(lambda x: x['tags'] + [x['general_topic']], axis=1)
        dummies_tags = pd.get_dummies(df_results.tags.apply(pd.Series).stack()).sum(level=0)
        dummies_tags[dummies_tags > 1] = 1
        # if null it is online service, put same lat/lon as user
        df_results['lat'] = df_results.lat.fillna(self.lat)
        df_results['lon'] = df_results.lon.fillna(self.lon)
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

        weights = np.concatenate(([0.005, 0.005], np.ones(overall_length) * 1.5))
        sim_matrix = Normalizer().transform(sim_matrix * weights)
        sim_values = cosine_similarity(sim_matrix)
        self.log().debug(sim_values)
        sim_vals = sim_values[len(df_results)][:len(df_results)]

        df_results['pocas_score'] = sim_vals
        df_results = df_results.sort_values('pocas_score', ascending=False)
        final_results = df_results[:int(self.top_n)]
        final_results = final_results.to_dict(orient='records')
        return final_results

    def del_none(self, d):
        """
        Delete keys with the value ``None`` in a dictionary, recursively.

        This alters the input so you may wish to ``copy`` the dict first.
        """
        for key, value in list(d.items()):
            if value is None:
                del d[key]
            elif type(value) == float:
                if np.isnan(value):
                    del d[key]
            elif isinstance(value, dict):
                self.del_none(value)
        return d

    def get_top_results(self):
        """
        Return Top Services

        :return:
        """
        self.get_lat_lon()
        self.tags = self.map_answers_tags()

        if len(self.tags) <= 1:
            self.tags = ['Public Benefits']
        m = MongoConnector()
        top_results = m.query_results(db=DB_SERVICES['db'], collection=DB_SERVICES['collection'],
                                      query={'$or': [{'tags': {'$in': self.tags}} , {'general_topic': {'$in': self.tags}}]},
                                      exclude={'loc': 0})
        self.log().debug(self.__dict__)
        try:
            final_results = self.run_similarity(top_results)
        except Exception:
            traceback.print_exc()
            self.log().warning('Could not run cosine sim, reverting to mongo query results')
            final_results = top_results[:int(self.top_n)]

        final = []
        for final_result in final_results:
            final.append(self.del_none(final_result))
        self.log().info(final)

        return final, {'lat': self.lat, 'lon': self.lon}
