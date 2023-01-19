# Airflow MongoDB/PostgresDB Backup/Restore Mangement
Docker-Compose management of Airflow to trigger backups of MongoDB and Postgres to Digital
Ocean object storage Spaces. Can trigger restoration of previous states as well. 


## Databases
### MongoDB
* Services Database
* Questions Database
* Admin User Database
* Analytics Database
### PostgresDB
* MHP frontend users 

## Airflow
### Daily Backup-Scheduler 
Schedule backups daily as compressed files to Digital Ocean Spaces using Boto3. 
### Restore Triggers
Schedule a restore based on argument of date to restore and database to restore. 

.env file 
```dotenv
SPACES_SECRET=xxxx
SPACES_KEY_ID=xxxx
SPACES_ENDPOINT=xxxx
SPACES_BUCKET=xxxx


AIRFLOW_FERNET_KEY=xxxx
AIRFLOW_SECRET_KEY=xxxx
AIRFLOW_EXECUTOR=CeleryExecutor
AIRFLOW_DATABASE_NAME=bitnami_airflow
AIRFLOW_DATABASE_USERNAME=bn_airflow
AIRFLOW_WEBSERVER_HOST=pocas_airflow
AIRFLOW_WEBSERVER_PORT_NUMBER=8080
AIRFLOW_DATABASE_PASSWORD=xxxx
AIRFLOW_LOAD_EXAMPLES=no

MONGO_INITDB_ROOT_USERNAME=xxxx
MONGO_INITDB_ROOT_PASSWORD=xxxx
MONGO_HOST=mongo_db
MONGO_PORT=27017

AIRFLOW_PASSWORD=xxxx
AIRFLOW_USERNAME=xxxx
AIRFLOW_EMAIL=xxxx

ALLOW_EMPTY_PASSWORD=yes
POSTGRESQL_DATABASE=bitnami_airflow
POSTGRESQL_USERNAME=bn_airflow
POSTGRESQL_PASSWORD=xxxx

ENV_POCAS=local

```