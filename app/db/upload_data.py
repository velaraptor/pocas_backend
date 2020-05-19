from db.mongo_connector import MongoConnector
import pandas as pd
import googlemaps
import os


def main():
    """
    Method to upload data from csv to Mongo and GeoCode with Google Maps API

    :return:
    """
    m = MongoConnector()
    file = os.getenv('SERVICES_CSV')
    if file is None:
        raise Exception('Add file to upload in local.env!')
    data = pd.read_csv(file)
    gmaps = googlemaps.Client(key=os.getenv('GOOGLE_KEY'))
    data['address'] = data.address.apply(lambda x: gmaps.geocode(x))
    data = data.to_dict(orient='records')
    m.upload_results(db='results', collection='services', data=data)


if __name__ == '__main__':
    main()
