from db.mongo_connector import MongoConnector
import pandas as pd
import numpy as np
import googlemaps
import os
import ast
import logging

logging.basicConfig(level=logging.INFO)


def parse_lat_lon(row):
    gmaps = googlemaps.Client(key=os.getenv('GOOGLE_KEY'))
    a = row['google_address']
    a = gmaps.geocode(a)
    if len(a) > 0:
        row['lat'] = a[0]['geometry']['location']['lat']
        row['lon'] = a[0]['geometry']['location']['lng']
    return row


def log():
    return logging.getLogger('upload_data')


def main():
    """
    Method to upload data from csv to Mongo and GeoCode with Google Maps API

    :return:
    """
    m = MongoConnector()
    file = os.getenv('SERVICES_CSV')
    if file is None:
        raise Exception('Add file to upload in local.env!')
    if os.getenv('GOOGLE_KEY') is None:
        raise Exception('Could not find Google Key! Set it in keys.env!')
    data = pd.read_csv(file)
    ids = np.arange(1, len(data) + 1)
    data['id'] = ids
    data['google_address'] = data.address + ' ' + data.city + ' ' + data.state + ' ' + data.zip_code.astype(str)
    data['tags'] = data.tags.apply(lambda x: ast.literal_eval(x))
    data = data.apply(lambda x: parse_lat_lon(x), axis=1)
    data = data[['name', 'phone', 'address', 'general_topic', 'tags',
                 'city', 'state', 'zip_code', 'web_site', 'lat', 'lon']]
    data = data.to_dict(orient='records')
    log().info(data)
    ids = m.upload_results(db='results', collection='services', data=data)
    log().info(ids)


if __name__ == '__main__':
    main()
