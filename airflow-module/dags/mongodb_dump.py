"""Dags for Backups of MongoDb and PostgresDB to S3 like object storage"""
# pylint: disable=W0104,W0640,R0801

import os
import pickle
import logging
from datetime import timedelta, datetime
from pymongo import MongoClient
from airflow import DAG
from airflow.decorators import task
import boto3
import pendulum
from bson.json_util import dumps

# https://medium.com/uncaught-exception/creating-mongodb-backup-in-s3-ac76ce27b228
# https://docs.digitalocean.com/reference/api/spaces-api/
# https://www.educba.com/postgres-dump-database/
# https://github.com/bitnami/containers/tree/main/bitnami/airflow
# https://airflow.apache.org/docs/apache-airflow/stable/howto/run-behind-proxy.html
# https://gist.github.com/ugnb/2b2121e74344139e56f6784ce6449916
logger = logging.getLogger("airflow.task")


class MongoConnector:
    """
    General MongoDB Connector
    """

    def __init__(self, fsync=False):
        self.__host = os.getenv("MONGO_HOST", "0.0.0.0")
        self.__port = os.getenv("MONGO_PORT", "27017")
        self.__pass = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
        self.__user = os.getenv("MONGO_INITDB_ROOT_USERNAME")

        uri = f"mongodb://{self.__user}:{self.__pass}@{self.__host}:{self.__port}"
        self.client = MongoClient(uri, fsync=fsync)

    def get_database(self, database):
        """Get Database"""
        return self.client.get_database(database)

    def close(self):
        """Close Client"""
        self.client.close()


def get_s3_client():
    """
    Get S3 client for Digital Ocean
    """
    session = boto3.session.Session()
    client = session.client(
        "s3",
        endpoint_url="https://sfo3.digitaloceanspaces.com",
        region_name="sfo3",  # Use the region in your endpoint.
        aws_access_key_id=os.getenv("SPACES_KEY_ID"),
        # Access key pair. You can create access key pairs using the control panel or API.
        aws_secret_access_key=os.getenv("SPACES_SECRET"),
    )
    return client


DATABASES = ["analytics", "users_login", "platform", "results"]
args = {"start_date": pendulum.datetime(2021, 1, 1, tz="UTC"), "depends_on_past": False}

dag = DAG(
    dag_id="mongodb_dump",
    default_args=args,
    schedule_interval=timedelta(days=1),
    is_paused_upon_creation=False,
    catchup=False,
    tags=["backup", "mongodb"],
)
dag.doc_md = """
# Daily backups to DigitalOcean of MongoDB
"""


def check_database_live(mongo_db):
    """
    Check if MongoDB is Live
    """
    m = MongoConnector()
    status = m.client.get_database(mongo_db).command("ping")
    return status


def backup_mongo_database(mongo_db):
    """Backup MongoDB to pickled file and send to S3 Bucket"""
    m = MongoConnector()
    database = m.get_database(mongo_db)
    collections = database.collection_names()
    directory_date = datetime.strftime(datetime.now(), "%m_%d_%Y")

    for collection_name in collections:
        col = database[collection_name]
        collection = col.find({})

        all_docs = []
        for document in collection:
            doc = dumps(document).encode()
            all_docs.append(doc)

        data_bytes = pickle.dumps(all_docs)
        s3_client = get_s3_client()
        env_pocas = os.getenv("ENV_POCAS", "local")
        s3_client.put_object(
            Bucket=os.getenv("SPACES_BUCKET"),
            Key=f"{env_pocas}/mongodb/{directory_date}/{mongo_db}/{collection_name}.json.gzip",
            Body=data_bytes,
            ACL="private",
        )
    m.close()


with dag as d:
    for db in DATABASES:

        @task(task_id=f"dump_mongo_{db}")
        def dump_database(database):
            """Airflow Dump Database"""
            backup_mongo_database(database)

        @task(task_id=f"check_mongo_db_{db}")
        def get_live(database):
            """Airflow check MongoDB"""
            return check_database_live(database)

        live_task = get_live(database=db)
        dump_task = dump_database(database=db)
        live_task >> dump_task
