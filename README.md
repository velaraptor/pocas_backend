# pocas_backend
![Code Coverage](https://github.com/velaraptor/pocas_backend/workflows/Code%20Coverage/badge.svg)

Flask API, Lambda, and Mongo DB Dockerized

## before running
Add keys.env file at top directory and add Google API Key
 * API_USER
* API_PASS
* GOOGLE_KEY
## to run
```
./start_services.sh
```
## ports open

 * MongoDB: http://0.0.0.0:27017
 * API: http://0.0.0.0/docs
 * ADMIN: http://0.0.0.0


# TODO: 
change secrets, put on digital ocean and buy domain, redirect to subdomains
https://stackoverflow.com/questions/53578729/docker-compose-make-container-available-under-subdomain
