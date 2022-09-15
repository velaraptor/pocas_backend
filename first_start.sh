# /bin/bash
./init-letsencrypt.sh
docker-compose -f docker-compose-prod.yml up -d --build