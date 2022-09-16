# pocas_backend
POCAS Backend. App can be found at https://mhpportal.app

![Code Coverage](https://github.com/velaraptor/pocas_backend/workflows/Code%20Coverage/badge.svg)
[![Digital Ocean Droplet](https://github.com/velaraptor/pocas_backend/actions/workflows/main.yml/badge.svg)](https://github.com/velaraptor/pocas_backend/actions/workflows/main.yml)
> Flask API, Lambda, and Mongo DB Dockerized

> Flask Frontend using BootsWatch

# LOCAL DEVELOPMENT
# PRE-COMMIT HOOKS
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
* ssh into Droplet and get Github Personal Access Token
```commandline
git clone https://github.com/velaraptor/pocas_backend
cd pocas_backend
git config credential.helper store
```
In top level directory cp file `ssh_start_prod.sh` for Github Actions

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
```
In `local.env` change the following to this:
> `SERVICES_CSV` to data file to be used to import services
```dotenv
SERVICES_CSV=/data/tfap_5.csv
RERUN_SERVICES=True
CREATE_USERS=True
```

First Time Run this and then wait 10 minutes
```commandline
./start_services.sh
sleep 300
docker-compose down 
```
## First Time on Production Sever
Will Update Cert every 12 hours automatically
*More Info: https://github.com/wmnnd/nginx-certbot

In `local.env` change the following to this:
```dotenv
RERUN_SERVICES=False
CREATE_USERS=False
```
`./init-letsencrypt.sh`

## Rerun Services
`./start_service_prod.sh`
