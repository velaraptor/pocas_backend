"""Dags for Backups of MongoDb and PostgresDB to S3 like object storage"""
import airflow.operators.bash
import boto3
import botocore
import os
from airflow import DAG
from airflow.operators.python import PythonOperator
import logging
from datetime import timedelta
from mongodb import MongoConnector
from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.bash import BashOperator
from airflow.providers.mongo.hooks.mongo import MongoHook

# TODO: DAG for mongodb dump daily to DigitalOcean Spaces
# https://medium.com/uncaught-exception/creating-mongodb-backup-in-s3-ac76ce27b228
# https://docs.digitalocean.com/reference/api/spaces-api/
# https://www.educba.com/postgres-dump-database/
# https://github.com/bitnami/containers/tree/main/bitnami/airflow
# https://airflow.apache.org/docs/apache-airflow/stable/howto/run-behind-proxy.html
# https://gist.github.com/ugnb/2b2121e74344139e56f6784ce6449916
logger = logging.getLogger("airflow.task")


# TODO: DAG for postgresdb user db to DigitalOcean Spaces


def get_s3_client():
    session = boto3.session.Session()
    client = session.client(
        "s3",
        endpoint_url=os.getenv("SPACES_ENDPOINT"),
        region_name="sfo3",  # Use the region in your endpoint.
        aws_access_key_id=os.getenv("SPACES_KEY_ID"),
        # Access key pair. You can create access key pairs using the control panel or API.
        aws_secret_access_key=os.getenv("SPACES_SECRET"),
    )


DATABASES = ["analytics", "users_login", "platform", "results"]
args = {"start_date": None, "owner": "airflow", "depends_on_past": False}

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


def check_database_live():
    m = MongoConnector()
    for db in DATABASES:
        status = m.client.get_database(db).command("ping")


with dag as d:
    check_db_live = PythonOperator(
        task_id="check_live", python_callable=check_database_live, dag=d
    )
