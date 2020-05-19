import os
import ast

DB_SERVICES = {'db': 'results', 'collection': 'services'}


def get_env_bool(env):
    return ast.literal_eval(os.getenv(env, 'False'))
