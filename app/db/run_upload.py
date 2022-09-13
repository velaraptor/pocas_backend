from db.upload_data import main as upload_data
from db.consts import get_env_bool
import logging

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] %(name)s [%(levelname)s]: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

rerun_upload_services = get_env_bool('RERUN_SERVICES')
if rerun_upload_services:
    logging.getLogger('top_n_results').info('Upload services from CSV')
    upload_data()
