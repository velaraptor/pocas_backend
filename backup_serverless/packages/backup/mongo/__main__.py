"""Serverless Function to Take MHP API data to S3"""
from utils.s3 import Mongo2S3

DATABASES = ["services", "questions", "platform"]


def main():
    """Run For each API Endpoint"""
    objects = []
    for endpoint in DATABASES:
        print(f"Checking endpoint: {endpoint}")
        obj = Mongo2S3(endpoint=endpoint)
        obj.check_api_live()
        print(f"API Status Code: {obj.status}")
        obj.backup_api()
        objects.append(obj.object_key)
    return {"objects": objects}
