"""Import Mongo 2 S3"""
import os
import pickle
from datetime import datetime
import requests
import boto3


class Mongo2S3:
    """MongoDB to S3"""

    def __init__(self, endpoint):
        self.__session = boto3.session.Session()
        self.region = os.getenv("SPACES_REGION")
        self.client = self.__session.client(
            "s3",
            endpoint_url=f"https://{self.region}.digitaloceanspaces.com",
            region_name=self.region,  # Use the region in your endpoint.
            aws_access_key_id=os.getenv("SPACES_KEY_ID"),
            # Access key pair. You can create access key pairs using the control panel or API.
            aws_secret_access_key=os.getenv("SPACES_SECRET"),
        )
        self.api = os.getenv("API_URL", "http://0.0.0.0")
        self.status = None
        self.endpoint = endpoint

    def check_api_live(self):
        """
        Check if API is Live
        """
        m = requests.get(f"{self.api}/api/v1/{self.endpoint}", timeout=5)
        self.status = m.status_code

    def backup_api(self):
        """Backup API to pickled file and send to S3 Bucket"""
        directory_date = datetime.strftime(datetime.now(), "%m_%d_%Y")

        if self.endpoint != "platform":
            resp = requests.get(f"{self.api}/api/v1/{self.endpoint}", timeout=5)
            data = resp.json()
        else:
            s = requests.Session()
            s.auth = (os.getenv("API_USER"), os.getenv("API_PASS"))
            resp = s.get(f"{self.api}/api/v1/{self.endpoint}/zip_codes", timeout=5)
            data = resp.json()
            data_zip_url = f"{self.api}/api/v1/platform/data/%s"
            json_data = []
            for z in data:
                resp = s.get(data_zip_url % z["id"], timeout=5)
                json_data = json_data + resp.json()
            data = json_data

        data_bytes = pickle.dumps(data)
        env_pocas = os.getenv("ENV_POCAS", "local")
        object_key = f"{env_pocas}/api/{directory_date}/{self.endpoint}/data.json.gzip"
        print(f"Writing object to key: {object_key}")
        self.client.put_object(
            Bucket=os.getenv("SPACES_BUCKET"),
            Key=object_key,
            Body=data_bytes,
            ACL="private",
        )
