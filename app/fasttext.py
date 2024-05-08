"""Text Model Class"""
import pickle
import time
import os
import sys
from datetime import datetime
import numpy as np
import nmslib
import boto3
from boto3.s3.transfer import TransferConfig
import compress_fasttext

# pylint: disable=C0209


class TextModel:
    """Run Text Model"""

    def __init__(self, epoch=40):
        self.epoch = epoch
        self.api_url = "https://mhpportal.app"
        self.services = None
        self.texts = []
        self.tok_text = []
        self.model_name = "_fasttext.model"
        self.weighted_doc_vects = []
        self.ft_model = None
        self.index = nmslib.init(method="hnsw", space="cosinesimil")
        self.__session = boto3.session.Session()

        self.region = os.getenv("SPACES_REGION", "sfo3")
        self.client = self.__session.client(
            "s3",
            endpoint_url=f"https://{self.region}.digitaloceanspaces.com",
            region_name=self.region,  # Use the region in your endpoint.
            aws_access_key_id=os.getenv("SPACES_KEY_ID", "DO00WXAJ82236KQQJWQC"),
            # Access key pair. You can create access key pairs using the control panel or API.
            aws_secret_access_key=os.getenv(
                "SPACES_SECRET", "tN6BrdAm3MW6IBBzcifF/Jt+D9zHN4DaVpzt/Qe185E"
            ),
        )
        self.object_key = None
        self.object_key_index = None

    def predict(self, search_query):
        """Predict services based on search query"""
        # querying the index:
        t0 = time.time()
        inpu = search_query.lower().split()
        query = [self.ft_model[vec] for vec in inpu]
        query = np.mean(query, axis=0)
        print(query)
        ids, distances = self.index.knnQuery(query, k=30)
        t1 = time.time()
        print(
            f"Searched {len(self.services)} records in {round(t1 - t0, 4)} seconds \n"
        )
        queried_ids = []
        for i, j in zip(ids, distances):
            if j < 0.4:
                queried_ids.append(self.services[i]["id"])
        print(queried_ids)
        return queried_ids

    def get_max_str_date(self):
        """Find Max Model in Spaces"""
        paginator = self.client.get_paginator("list_objects")
        dates = []
        result = paginator.paginate(
            Bucket=os.getenv("SPACES_BUCKET", "mhpportal"),
            Delimiter="/",
            Prefix="model/",
        )
        for prefix in result.search("CommonPrefixes"):
            folder = datetime.strptime(prefix.get("Prefix").split("/")[-2], "%m_%d_%Y")
            dates.append(folder)
        max_date = max(dates)
        max_str_date = datetime.strftime(max_date, "%m_%d_%Y")
        return max_str_date

    def load_recent_model(self):
        """Load Model from Spaces"""
        max_str_date = self.get_max_str_date()
        payload = self.client.get_object(
            Bucket=os.getenv("SPACES_BUCKET", "mhpportal"),
            Key=f"model/{max_str_date}/model.pickle",
        )
        data = pickle.loads(payload["Body"].read())
        self.services = data["services"]
        self.index.loadIndex("index.bin")
        self.ft_model = compress_fasttext.models.CompressedFastTextKeyedVectors.load(
            "ft_model_2.bin"
        )

    def download_model(self):
        """Download Models"""
        max_str_date = self.get_max_str_date()
        config = TransferConfig(
            multipart_threshold=1024 * 50,
            max_concurrency=15,
            multipart_chunksize=1024 * 50,
            use_threads=True,
        )

        self.client.download_file(
            os.getenv("SPACES_BUCKET", "mhpportal"),
            f"model/{max_str_date}/index.bin",
            "index.bin",
        )
        meta_data = self.client.head_object(
            Bucket=os.getenv("SPACES_BUCKET", "mhpportal"),
            Key=f"model/{max_str_date}/ft_model.pickle",
        )
        total_length = int(meta_data.get("ContentLength", 0))
        downloaded = 0

        def progress(chunk):
            nonlocal downloaded
            downloaded += chunk
            done = int(50 * downloaded / total_length)
            sys.stdout.write(
                "\r[%s%s]  (%.2f%%)" % ("=" * done, " " * (50 - done), done * 2)
            )
            sys.stdout.flush()

        with open("ft_model_2.bin", "wb") as file:
            self.client.download_fileobj(
                Bucket=os.getenv("SPACES_BUCKET", "mhpportal"),
                Config=config,
                Key=f"model/{max_str_date}/ft_model.bin",
                Fileobj=file,
                Callback=progress,
            )


if __name__ == "__main__":
    f = TextModel()
    f.download_model()
