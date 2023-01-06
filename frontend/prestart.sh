#! /usr/bin/env bash
# Runs static services from csv when first start running, be sure to add to env file RERUN_SERVICES=True
sleep 10;
# Run migrations

set -e
echo 'Performing any database migrations.'
DATE=$(date +"%Y_%m_%d_%H_%M")
python frontend/create_db.py db migrate -m "${DATE}"

python frontend/create_db.py db upgrade
