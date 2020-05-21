from db.upload_data import main as upload_data
from db.consts import get_env_bool


rerun_upload_services = get_env_bool('RERUN_SERVICES')
if rerun_upload_services:
    upload_data()