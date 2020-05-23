import os
import ast
import googlemaps

DB_SERVICES = {'db': 'results', 'collection': 'services'}


def get_env_bool(env):
    return ast.literal_eval(os.getenv(env, 'False'))


def get_lat_lon(model):
    google_address = model.get('address') + ' ' + model.get('city') + ' ' + \
                     model.get('state') + ' ' + str(model.get('zip_code'))

    gmaps = googlemaps.Client(key=os.getenv('GOOGLE_KEY'))
    a = gmaps.geocode(google_address)
    if len(a) > 0:
        lat = a[0]['geometry']['location']['lat']
        lon = a[0]['geometry']['location']['lng']
        loc = [lon, lat]
        model['loc'] = loc
        model['lat'] = lat
        model['lon'] = lon
    return model