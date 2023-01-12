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