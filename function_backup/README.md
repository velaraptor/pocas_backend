# Backup MongoDB to DigitalOcean Spaces
> Use POCAS-API to get recent questions, user results and services

Creates a file systemm in the following format:
```
{env}/api/{date}/{endpoint}/data.json.gzip

# example
prod/api/01_20_2023/questions/data.json.gzip
```

## Prerequisites
* `doctl` https://docs.digitalocean.com/reference/doctl/how-to/install/
* Digital Ocean Personal Access Token

## Deploy Serverless Function to Neo4j
```shell
# deploy function
doctl serverless deploy . -v
# trigger function
doctl sls fn invoke joke
```
