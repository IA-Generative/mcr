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
      # Map form to stay merge-compatible with the base compose, which sets a
      # keycloak.localhost alias on mcr-network.
      mcr-network:
        aliases:
          - keycloak.localhost
      shared-network: {}

networks:
  shared-network:
    external: true
