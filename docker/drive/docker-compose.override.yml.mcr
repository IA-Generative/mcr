# Drive integration override for MCR
# Copied to docker-compose.override.yml by docker/drive/setup-drive.sh
# Adds shared-network to services that need to reach Drive containers

services:
  meeting:
    networks:
      - mcr-network
      - shared-network

  keycloak:
    networks:
      - mcr-network
      - shared-network

networks:
  shared-network:
    external: true
