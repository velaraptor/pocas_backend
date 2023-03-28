#! /usr/bin/env bash

# Runs static services from csv when first start running, be sure to add to env file RERUN_SERVICES=True
python /app/db/run_upload.py
python /app/db/mongo_index.py
python /app/fasttext.py