from db.mongo_connector import MongoConnector
import pandas as pd
import googlemaps
import os


def main():
    m = MongoConnector()
    data = pd.read_csv('/data/services.csv').to_dict(orient='records')
    gmaps = googlemaps.Client(key=os.getenv('GOOGLE_KEY'))
    data['address'] = data.address.apply(lambda x: gmaps.geocode(x))

    m.upload_results(db='results', collection='services', data=data)


if __name__ == '__main__':
    main()
