# <img src="frontend/static/icon.png" height="60" width="60" > MHP Portal

POCAS Backend. App can be found at https://mhpportal.app

![Code Coverage Flake8](https://github.com/velaraptor/pocas_backend/workflows/Code%20Coverage/badge.svg)
[![Pylint](https://github.com/velaraptor/pocas_backend/actions/workflows/pylint.yml/badge.svg)](https://github.com/velaraptor/pocas_backend/actions/workflows/pylint.yml)
[![Digital Ocean Droplet](https://github.com/velaraptor/pocas_backend/actions/workflows/main.yml/badge.svg)](https://github.com/velaraptor/pocas_backend/actions/workflows/main.yml)
![version](https://img.shields.io/badge/version-1.1-blue)
> Flask API, Lambda, and Mongo DB Dockerized

> Flask Frontend using BootsWatch

* [Local Development](#local-development)
* [Prod Environment](#production)
* [Additional Modules](#additional-modules)


# LOCAL DEVELOPMENT
### PRE-COMMIT HOOKS
```commandline
pip install -r requirements-pre-commit.txt
pre-commit install
```

### Before running
Then add `keys.env` in this format
```dotenv
GOOGLE_KEY=xxxx
API_USER=xxxx
API_PASS=xxxx
```
### To Run
```
./start_services.sh
```
### Ports Open for Local Dev

 * MongoDB: http://0.0.0.0:27017
 * PostGreSQL: http://0.0.0.0:5432
 * API: http://0.0.0.0/api/v1/docs
 * ADMIN: http://0.0.0.0/admin
 * FRONTEND: http://0.0.0.0



# PRODUCTION
* First get domain through Google Domains and change NameServers to Point to DigitalOcean
& Add `A` to DigitalOcean Networking Command Panel
* ssh into Droplet and get GitHub Personal Access Token
```commandline
git clone https://github.com/velaraptor/pocas_backend
cd pocas_backend
git config credential.helper store
```
In top level directory cp file `ssh_start_prod.sh` for GitHub Actions

```commandline
cp ssh_start_prod.sh ~/
```

In `local.env` change the RECAPTCHA to Google one that works. the following is local testing keys
```dotenv
RECAPTCHA_PUBLIC_KEY=6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI
RECAPTCHA_PRIVATE_KEY=6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe
```

Then add `keys.env` in this format
```dotenv
GOOGLE_KEY=xxxx
API_USER=xxxx
API_PASS=xxxx
FLASK_SECRET_KEY=xxxx
MAIL_USERNAME=xxxx@mhpportal.app
MAIL_PASSWORD=xxxx
```
In `local.env` change the following to this:
> `SERVICES_CSV` to data file to be used to import services
```dotenv
SERVICES_CSV=/data/tfap_5.csv
RERUN_SERVICES=True
CREATE_USERS=True
FIRST_QUESTIONS=True
```

First Time Run this and then wait 10 minutes
```bash
./start_services.sh
sleep 300
docker-compose down 
```
## First Time on Production Sever
Will Update Cert every 12 hours automatically
* More Info: https://github.com/wmnnd/nginx-certbot

In `local.env` change the following to this:
```dotenv
RERUN_SERVICES=False
CREATE_USERS=False
FIRST_QUESTIONS=False
```
`./init-letsencrypt.sh`

## Rerun Services
`./start_service_prod.sh`


# Additional Modules
* [Serverless Backup](/backup_serverless)
  * Currently, can back up MongoDB to Digital Oceans Spaces
* [Neo4j](/graph_db) 
  * For adding MHP Services and Questions in graph database, currently an EDA project.
    * Future uses for predicting tags and similar questions, nearest neighbors as additional algorithm, services/tags not tied to question alarm.