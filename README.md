# pocas_backend
![Code Coverage](https://github.com/velaraptor/pocas_backend/workflows/Code%20Coverage/badge.svg)

Flask API, Lambda, and Mongo DB Dockerized

## before running
Add keys.env file at top directory and add Google API Key

## to run
```
./start_services.sh
```
## ports open

 * MongoDB: http://0.0.0.0:27017
 * API: http://0.0.0.0/api/v1
 * ADMIN: http://0.0.0.0
  
    * ```$VERSION``` is set in local.env; is int, for example ```v1```
