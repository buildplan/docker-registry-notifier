### This image can be used alongside registry:3 (https://hub.docker.com/_/registry) to configure notifications for your private docker registry.

#### Docker compose example:

```
networks:
  registry-net:
    driver: bridge

services:
  # --- registry ---
  registry:
    image: registry:3.0.0
    container_name: registry_service
    volumes: # create volumes before starting the containers
      - ./docker-registry/data:/var/lib/registry
      - ./docker-registry/config.yml:/etc/distribution/config.yml:ro
    networks:
      - registry-net
    environment:
      OTEL_TRACES_EXPORTER: "none"
      REGISTRY_HTTP_SECRET: ${REGISTRY_HTTP_SECRET} # add in .env
    restart: unless-stopped

  # --- NOTIFICATION APP SERVICE ---
  registry-webhook-receiver:
    image: iamdockin/registry-webhook-receiver:latest # Or your new image name/tag after rebuilding
    container_name: registry-webhook-receiver
    restart: unless-stopped
    networks:
      - registry-net
    ports: # Optional: if you need to access it directly for testing, otherwise remove if only internal
      - "5001:5001"
    environment:
      # --- General Settings ---
      - NOTIFICATION_SERVICE_TYPE=${NOTIFICATION_SERVICE_TYPE:-ntfy} # Default to ntfy if not set
      - NOTIFICATION_PRIORITY=${NOTIFICATION_PRIORITY:-default}

      # --- Ntfy Settings (only needed if NOTIFICATION_SERVICE_TYPE is 'ntfy') ---
      - NTFY_SERVER_URL=${NTFY_SERVER_URL}
      - NTFY_TOPIC=${NTFY_TOPIC}
      - NTFY_ACCESS_TOKEN=${NTFY_ACCESS_TOKEN} # Optional

      # --- Gotify Settings (only needed if NOTIFICATION_SERVICE_TYPE is 'gotify') ---
      - GOTIFY_SERVER_URL=${GOTIFY_SERVER_URL}
      - GOTIFY_APP_TOKEN=${GOTIFY_APP_TOKEN}

      # --- Discord Settings (only needed if NOTIFICATION_SERVICE_TYPE is 'discord') ---
      - DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}

      # --- Flask Settings ---
      - FLASK_ENV=production
    # If you use a .env file in the same directory as your docker-compose.yml:
    # env_file:
    #  - .env
```

#### Update your config.yml example below:

```
version: 0.1
log:
  level: info
  formatter: text
storage:
  filesystem:
    rootdirectory: /var/lib/registry
  delete:
    enabled: true
http:
  addr: :5000
  secret: some-very-long-string-here # same as in .env
notifications:
  endpoints:
    - name: "mycustomntfyreceiver"
      url: "http://registry-webhook-receiver:5001/notify"
      timeout: 5s
      threshold: 3
      backoff: 10s
```

#### Create a .env file example:

```
REGISTRY_HTTP_SECRET=some-very-long-string-here

NTFY_SERVER_URL=https://ntfy.myserver.tld
NTFY_TOPIC=my_private_registry
NTFY_ACCESS_TOKEN=tk_xxxxxxxxxx # access token from ntfy
NTFY_PRIORITY=default
```
