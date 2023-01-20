"""Severless Function to Take MHP API data to S3"""
import os
import pickle
from datetime import datetime
import requests
import boto3


API_URL = os.getenv("API_URL", "http://0.0.0.0")
DATABASES = ["services", "questions", "platform"]


def get_s3_client():
    """
    Get S3 client for Digital Ocean
    """
    session = boto3.session.Session()
    region = os.getenv("SPACES_REGION")
    client = session.client(
        "s3",
        endpoint_url=f"https://{region}.digitaloceanspaces.com",
        region_name=region,  # Use the region in your endpoint.
        aws_access_key_id=os.getenv("SPACES_KEY_ID"),
        # Access key pair. You can create access key pairs using the control panel or API.
        aws_secret_access_key=os.getenv("SPACES_SECRET"),
    )
    return client


def check_api_live(endpoint):
    """
    Check if API is Live
    """
    m = requests.get(f"{API_URL}/api/v1/{endpoint}", timeout=5)
    return m.status_code


def backup_api(endpoint):
    """Backup API to pickled file and send to S3 Bucket"""
    directory_date = datetime.strftime(datetime.now(), "%m_%d_%Y")

    if endpoint != "platform":
        resp = requests.get(f"{API_URL}/api/v1/{endpoint}", timeout=5)
        data = resp.json()
    else:
        resp = requests.get(f"{API_URL}/api/v1/{endpoint}/zip_codes", timeout=5)
        data = resp.json()
        data_zip_url = f"{API_URL}/api/v1/platform/data/%s"
        json_data = []
        for z in data:
            resp = requests.get(data_zip_url % z["id"], timeout=5)
            json_data = json_data + resp.json()
        data = json_data

    data_bytes = pickle.dumps(data)
    s3_client = get_s3_client()
    env_pocas = os.getenv("ENV_POCAS", "local")
    object_key = f"{env_pocas}/api/{directory_date}/{endpoint}/data.json.gzip"
    print(f"Writing object to key: {object_key}")
    s3_client.put_object(
        Bucket=os.getenv("SPACES_BUCKET"),
        Key=object_key,
        Body=data_bytes,
        ACL="private",
    )


def main():
    """Run For each API Endpoint"""
    for endpoint in DATABASES:
        print(f"Checking endpoint: {endpoint}")
        status = check_api_live(endpoint)
        print(f"API Status Code: {status}")
        backup_api(endpoint)
