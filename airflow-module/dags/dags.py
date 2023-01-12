"""Dags for Backups of MongoDb and PostgresDB to S3 like object storage"""
import boto3
from airflow import DAG

# TODO: DAG for mongodb dump daily to DigitalOcean Spaces


# TODO: DAG for postgresdb user db to DigitalOcean Spaces
session = boto3.session.Session()

with DAG as dag:
    pass
