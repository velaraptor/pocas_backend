# pocas_backend
Flask API, Lambda, and Mongo DB Dockerized

## before running
Add keys.env file at top directory and add Google API Key

## to run
```
./start_services.sh
```
## ports open

 * MongoDB: http://0.0.0.0:27017
 * API: http://0.0.0.0:8080/api/v1
  
    * ```$VERSION``` is set in local.env; is int, for example ```v1```
