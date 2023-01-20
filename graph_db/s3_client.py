"""S3 Client"""
# pylint: disable=C0209
import os
import pickle
from datetime import datetime
import boto3


class S3Importer:
    """Import from Digital Ocean"""

    def __init__(self):
        self.session = boto3.session.Session()
        self.env_pocas = os.getenv("POCAS_ENV", "prod")
        self.region = os.getenv("SPACES_REGION")
        self.client = self.session.client(
            "s3",
            endpoint_url=f"https://{self.region}.digitaloceanspaces.com",
            region_name=self.region,  # Use the region in your endpoint.
            aws_access_key_id=os.getenv("SPACES_KEY_ID"),
            # Access key pair. You can create access key pairs using the control panel or API.
            aws_secret_access_key=os.getenv("SPACES_SECRET"),
        )

    def get_object(self, path):
        """Get Object from path"""
        payload = self.client.get_object(
            Bucket=os.getenv("SPACES_BUCKET", "mhpportal"),
            Key=f"{self.env_pocas}/mongodb/{path}",
        )
        data = pickle.loads(payload["Body"].read())
        return data

    def find_recent_mongo(self):
        """Find most recent directory in bucket"""
        paginator = self.client.get_paginator("list_objects")
        dates = []
        result = paginator.paginate(
            Bucket=os.getenv("SPACES_BUCKET", "mhpportal"),
            Delimiter="/",
            Prefix=f"{self.env_pocas}/mongodb/",
        )
        for prefix in result.search("CommonPrefixes"):
            folder = datetime.strptime(prefix.get("Prefix").split("/")[-2], "%m_%d_%Y")
            dates.append(folder)
        max_date = max(dates)
        return datetime.strftime(max_date, "%m_%d_%Y")
