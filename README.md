# Docker Registry Notifier

A lightweight, multi-architecture webhook receiver to get notifications from your private Docker Registry. It listens for image push events and sends clean, debounced alerts to your favorite notification service.

This image is designed to be used alongside the official [`registry:3`](https://hub.docker.com/_/registry) image.

## Key Features

  - **Multiple Notification Services:** Supports **ntfy**, **Gotify**, and **Discord** out of the box.
  - **Debounced Notifications:** Intelligently groups multiple push events for a single image tag into one notification, preventing alert spam.
  - **Lightweight & Secure:** Built using multi-stage Docker builds for a minimal final image size and runs as a non-root user for enhanced security.
  - **Multi-Arch Support:** The image is built for both `linux/amd64` and `linux/arm64` architectures, so it can run anywhere from a cloud VM to a Raspberry Pi.

## Getting Started

### Step 1: Configure Your Docker Registry

Your Docker Registry needs to be configured to send webhook notifications to this service. Add the `notifications` section to your registry's `config.yml`.

**Example `config.yml`:**

```yaml
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
  secret: "a-very-secure-secret-string" # Replace with your own secret
notifications:
  endpoints:
    - name: "notifier"
      url: "http://registry-notifier:5001/notify" # The URL points to our service
      timeout: 5s
      threshold: 1 # Send notification after 1 event
      backoff: 10s
```

### Step 2: Prepare the Notifier Configuration

Create a `.env` file to store your configuration secrets and settings. This is more secure than placing them directly in the `docker-compose.yml` file.

**Example `.env` file:**

```env
# The same secret used in your registry's config.yml
REGISTRY_HTTP_SECRET="a-very-secure-secret-string"

# --- CORE NOTIFIER SETTINGS ---
# Choose ONE service: "ntfy", "gotify", or "discord"
NOTIFICATION_SERVICE_TYPE=ntfy

# Cooldown period in seconds to prevent duplicate notifications for the same image tag.
DEBOUNCE_SECONDS=10

# --- NOTIFICATION PRIORITY ---
# Options: min, low, default, high, max
NOTIFICATION_PRIORITY=default

# --- NTFY SETTINGS (if using ntfy) ---
NTFY_SERVER_URL=https://ntfy.sh
NTFY_TOPIC=my_registry_events
NTFY_ACCESS_TOKEN= # Optional: your_ntfy_access_token

# --- GOTIFY SETTINGS (if using gotify) ---
GOTIFY_SERVER_URL= # https://your-gotify-instance.com
GOTIFY_APP_TOKEN= # your_gotify_app_token

# --- DISCORD SETTINGS (if using discord) ---
DISCORD_WEBHOOK_URL= # https://discord.com/api/webhooks/...
```

### Step 3: Create the Docker Compose File

This `docker-compose.yml` will run both your Docker Registry and the new notifier service.

**Example `docker-compose.yml`:**

```yaml
networks:
  registry-net:
    driver: bridge

services:
  # --- Docker Registry ---
  registry:
    image: registry:3
    container_name: registry_service
    restart: unless-stopped
    volumes:
      - ./data:/var/lib/registry
      - ./config.yml:/etc/docker/registry/config.yml:ro
    networks:
      - registry-net
    environment:
      REGISTRY_HTTP_SECRET: ${REGISTRY_HTTP_SECRET} # Loaded from .env file

  # --- Notification Service ---
  registry-notifier:
    # Replace with your own image if you build it yourself
    image: iamdockin/registry-webhook-receiver:latest
    container_name: registry-notifier
    restart: unless-stopped
    networks:
      - registry-net
    # The .env file in the same directory will be loaded automatically
    env_file: .env
```

### Step 4: Launch the Services

With your `config.yml`, `.env`, and `docker-compose.yml` files in the same directory, simply run:

```bash
docker-compose up -d
```

Your registry is now running and will send notifications via the notifier service whenever a new image is pushed\!

## Building The Image Yourself

If you wish to modify the script or build the image yourself, follow these instructions.

### Building for a Single Architecture

```bash
docker build -t your-username/registry-notifier:latest .
```

### Building for Multi-Architecture (Recommended)

To build for both `amd64` and `arm64`, you must use `docker buildx` and push the result directly to a registry.

```bash
# This command builds for both platforms and pushes the manifest to your registry
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t your-username/registry-notifier:latest \
  --push .
```

## Configuration Environment Variables

| Variable                      | Description                                                                                              | Required?                                 | Default |
| ----------------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------- | ------- |
| `NOTIFICATION_SERVICE_TYPE`   | The notification service to use.                                                                         | **Yes** | `ntfy`  |
| `DEBOUNCE_SECONDS`            | Seconds to wait before allowing another notification for the same image tag.                               | No                                        | `10`    |
| `NOTIFICATION_PRIORITY`       | Priority for ntfy/Gotify messages. Options: `min`, `low`, `default`, `high`, `max`.                      | No                                        | `default` |
| `NTFY_SERVER_URL`             | The URL of your ntfy server.                                                                             | If `NOTIFICATION_SERVICE_TYPE` is `ntfy`  |         |
| `NTFY_TOPIC`                  | The ntfy topic to publish to.                                                                            | If `NOTIFICATION_SERVICE_TYPE` is `ntfy`  |         |
| `NTFY_ACCESS_TOKEN`           | An optional access token for ntfy.                                                                       | No                                        |         |
| `GOTIFY_SERVER_URL`           | The URL of your Gotify server.                                                                           | If `NOTIFICATION_SERVICE_TYPE` is `gotify`|         |
| `GOTIFY_APP_TOKEN`            | The application or client token for Gotify.                                                              | If `NOTIFICATION_SERVICE_TYPE` is `gotify`|         |
| `DISCORD_WEBHOOK_URL`         | The full URL for your Discord webhook.                                                                   | If `NOTIFICATION_SERVICE_TYPE` is `discord`|         |

-----
