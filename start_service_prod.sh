# /bin/bash

cd pocas_backend
git pull
docker-compose -f docker-compose-prod.yml up -d --build