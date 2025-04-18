"""Get Tio Results Back"""
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

# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611, W0702

AGE_MAPPER = {
    "Elder": [51, 120],
    "Adult": [36, 50],
    "Young Adult Resources": [21, 35],
    "Adolescent": [0, 20],
}


def get_all_collection(collection, exclude=None):
    """Get all Collection Documents"""
    m = MongoConnector(fsync=True)
    data = m.query_results_api(
        db=DB_SERVICES["db"],
        collection=collection,
        query={},
        exclude=exclude,
    )
    return data


def get_all_services():
    """Get all Services"""
    all_services = get_all_collection(DB_SERVICES["collection"], {"loc": 0})
    return all_services


def get_all_questions():
    """Get all Questions"""
    all_questions = get_all_collection("questions")
    return all_questions


def get_all_tags_services():
    """Get all tags from Collection Services"""
    return get_all_tags_collection(main_tag="general_topic", data_exc=get_all_services)


def get_all_tags_questions():
    """Get all tags from collection questions"""
    return get_all_tags_collection(main_tag="main_tag", data_exc=get_all_questions)


def get_all_tags_collection(
    main_tag="general_topic", tags="tags", data_exc=get_all_services
):
    """Generic Function to get all Tags"""
    try:
        all_data = data_exc()
        data = pd.DataFrame(all_data)
        g_t = data[main_tag].dropna().unique().tolist()
        tags = data[tags].explode().dropna().unique().tolist()
        values = set(g_t + tags)
        values = sorted(values)
    except:  # noqa: E722
        values = []
    return values


ALL_TAGS = get_all_tags_services()
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class GetTopNResults:
    """Cosine Similarity on User Results compared to Tags from Services"""

    def __init__(self, top_n, dob, answers, address):
        self.top_n = top_n if top_n != 0 else 1
        self.__address = address
        self.dob = datetime.strptime(str(dob), "%m%d%Y")
        self.answers = answers
        self.lat = None
        self.lon = None
        self.age = self.get_age()
        self.tags = []
        self.meter_to_mile = 1609
        self.miles = 200

    def get_lat_lon(self):
        """
        Get Lat/Lon of User address from Google GeoCode API
        """
        if os.getenv("GOOGLE_KEY") is None:
            raise Exception("Could not find Google Key! Set it in keys.env!")
        gmaps = googlemaps.Client(key=os.getenv("GOOGLE_KEY"))
        address = gmaps.geocode(self.__address)
        self.lat = address[0]["geometry"]["location"]["lat"]
        self.lon = address[0]["geometry"]["location"]["lng"]

    @staticmethod
    def log():
        """Logger for TopNResults"""
        return logging.getLogger("top_n_results")

    def get_age(self):
        """
        Get Age in Years
        :return: int
        """
        today = datetime.today()
        years = today.year - self.dob.year
        if today.month == self.dob.month and today.day < self.dob.day:
            years -= 1
        return years

    def map_answers_tags(self, questions):
        """
        Map Questionnaire to Mapper

        :return: Array of Tags Matched
        """
        answers = self.answers
        age_df = pd.DataFrame(AGE_MAPPER)
        vals = np.min(np.abs(age_df - self.age), axis=0)
        self.log().debug(vals)

        age_tags = vals[vals == np.min(vals)].index.values[0]

        # find tags from questions

        # make binary to boolean
        bool_answers = list(map(bool, answers))
        # filter questions that were answered yes
        answers_to_use = np.array(questions)[bool_answers]

        # add all tags from yes answered questions
        tags_user = []
        for answer in answers_to_use:
            tags_user = tags_user + answer["tags"]

        # add question and age tags
        answer_tags = tags_user + [age_tags]
        # remove dups
        answer_tags = list(set(answer_tags))
        return answer_tags

    def find_radius(self):
        """Find within 200 miles of services"""
        m = MongoConnector()
        db = DB_SERVICES["db"]
        collection = DB_SERVICES["collection"]
        query = {
            "$geoNear": {
                "near": {"type": "Point", "coordinates": [self.lon, self.lat]},
                "distanceField": "dist.calculated",
                "maxDistance": int(self.miles * self.meter_to_mile),  # in meteres
                "spherical": True,
            }
        }
        results = m.aggregate(db, collection, query=query)
        if len(results) > 0:
            return True
        return False

    def run_similarity(self, results):
        """
        run cosine similarity and euclidean distance, get top n, normalize lat/lon
        :param results:
        :return:
        """

        df_results = pd.DataFrame(results)
        df_results["tags"] = df_results.apply(
            lambda x: x["tags"] + [x["general_topic"]], axis=1
        )
        dummies_tags = (
            pd.get_dummies(df_results.tags.apply(pd.Series).stack())
            .groupby(level=0)
            .sum()
        )
        dummies_tags[dummies_tags > 1] = 1
        # if null it is online service, put same lat/lon as user
        df_results["lat"] = df_results.lat.fillna(self.lat)
        df_results["lon"] = df_results.lon.fillna(self.lon)
        matrix = pd.concat([df_results[["lat", "lon"]], dummies_tags], axis=1)
        matrix_val = matrix.values
        tags_unique = dummies_tags.columns.values
        overall_length = len(tags_unique)

        empty_user_tags = pd.DataFrame([np.zeros(overall_length)], columns=tags_unique)
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
        sim_vals = sim_values[len(df_results)][: len(df_results)]

        df_results["pocas_score"] = sim_vals
        df_results = df_results.sort_values("pocas_score", ascending=False)
        df_results = df_results.drop_duplicates(subset="name")
        final_results = df_results[: int(self.top_n)]
        final_results.loc[final_results["online_service"] == 1, "lat"] = None
        final_results.loc[final_results["online_service"] == 1, "lon"] = None

        final_results = final_results.to_dict(orient="records")
        return final_results

    def del_none(self, d):
        """
        Delete keys with the value ``None`` in a dictionary, recursively.

        This alters the input, so you may wish to ``copy`` the dict first.
        """
        for key, value in list(d.items()):
            if value is None:
                del d[key]
            elif isinstance(value, float):
                if np.isnan(value):
                    del d[key]
            elif isinstance(value, dict):
                self.del_none(value)
        return d

    @staticmethod
    def get_questions(mongo_connector: MongoConnector, collection="questions"):
        """
        Get Questions from MongoDB
        """
        db = mongo_connector.client[DB_SERVICES["db"]]
        c = db[collection]
        results = []
        for c in c.find().sort("id"):
            results.append(c)
        return results

    def get_top_results(self):
        """
        Return Top Services

        :return:
        """
        self.get_lat_lon()
        m = MongoConnector()
        questions = self.get_questions(m)

        self.tags = self.map_answers_tags(questions)
        if len(self.tags) <= 1:
            self.tags.append("Public Benefits")
        self.log().debug(self.tags)

        # https://stackoverflow.com/questions/23188875/mongodb-unable-to-find-index-for-geonear-query
        top_results = m.query_results(
            db=DB_SERVICES["db"],
            collection=DB_SERVICES["collection"],
            query={
                "loc": {
                    "$near": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": [self.lon, self.lat],
                        },
                        "$maxDistance": int(self.miles * self.meter_to_mile),
                    }
                },
                "$or": [
                    {"tags": {"$in": self.tags}},
                    {"general_topic": {"$in": self.tags}},
                ],
            },
        )
        online_results = m.query_results(
            db=DB_SERVICES["db"],
            collection=DB_SERVICES["collection"],
            query={
                "loc": None,
                "$or": [
                    {"tags": {"$in": self.tags}},
                    {"general_topic": {"$in": self.tags}},
                ],
            },
        )
        self.log().debug(self.__dict__)
        self.log().debug(online_results)
        self.log().debug(top_results)
        top_results = online_results + top_results
        try:
            final_results = self.run_similarity(top_results)
        except Exception:
            traceback.print_exc()
            self.log().warning(
                "Could not run cosine sim, reverting to mongo query results"
            )
            final_results = top_results[: int(self.top_n)]

        final = []
        for final_result in final_results:
            final.append(self.del_none(final_result))
        self.log().debug(final)

        return final, {"lat": self.lat, "lon": self.lon}
