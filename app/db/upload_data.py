"""Method to take CSV and format for upload to Mongo"""
import os
import ast
import logging
from db.mongo_connector import MongoConnector
from db.consts import DB_SERVICES
import pandas as pd
import numpy as np
import googlemaps
from bson.objectid import ObjectId

# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611, W0108. W0702

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def parse_lat_lon(row):
    """Parse Lat/Long from Address through Google API"""
    gmaps = googlemaps.Client(key=os.getenv("GOOGLE_KEY"))
    try:
        if row["no_address"] == 0:
            a = row["google_address"]
            a = gmaps.geocode(a)
            if len(a) > 0:
                row["lat"] = a[0]["geometry"]["location"]["lat"]
                row["lon"] = a[0]["geometry"]["location"]["lng"]
            row["loc"] = [row["lon"], row["lat"]]
            row["online_service"] = 0
        else:
            row["lat"] = None
            row["lon"] = None
            row["loc"] = None
            row["online_service"] = 1
    except:  # noqa: E722
        row["lat"] = None
        row["lon"] = None
        row["loc"] = None
        row["online_service"] = 1
    return row


def get_tags(x):
    """Get Tags from Array in column and cast as List"""
    if isinstance(x, str):
        return ast.literal_eval(x)
    return []


def log():
    """Logging Logger"""
    return logging.getLogger("upload_data")


def main():
    """
    Method to upload data from csv to Mongo and GeoCode with Google Maps API

    :return:
    """
    m = MongoConnector()
    collection = m.client.results.services
    for doc in collection.find({}):
        collection.delete_one({"_id": ObjectId(doc["_id"])})
    file = os.getenv("SERVICES_CSV")
    if file is None:
        raise Exception("Add file to upload in local.env!")
    if os.getenv("GOOGLE_KEY") is None:
        raise Exception("Could not find Google Key! Set it in keys.env!")
    data = pd.read_csv(file)
    log().info("Size of Services: %s", str(len(data)))
    ids = np.arange(1, len(data) + 1)
    data["id"] = ids
    data["google_address"] = (
        data.address
        + " "
        + data.city
        + " "
        + data.state
        + " "
        + data.zip_code.astype(str)
    )
    data["tags"] = data.tags.apply(lambda x: get_tags(x))
    data = data.apply(lambda x: parse_lat_lon(x), axis=1)
    data = data[
        [
            "name",
            "phone",
            "address",
            "general_topic",
            "tags",
            "city",
            "state",
            "zip_code",
            "web_site",
            "lat",
            "lon",
            "loc",
            "online_service",
            "hours",
            "days",
        ]
    ]
    data.zip_code = pd.to_numeric(data.zip_code, errors="coerce").astype("Int64")
    data = data.where(pd.notnull(data), None)
    data = data.replace({np.nan: None})
    data = data.to_dict(orient="records")
    log().info(data)
    ids = m.upload_results(
        db=DB_SERVICES["db"],
        collection=DB_SERVICES["collection"],
        data=data,
        geo_index=True,
    )
    log().info(ids)


if __name__ == "__main__":
    main()
