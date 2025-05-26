FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Environment variables will be set in docker-compose.yml or .env file
# ENV NOTIFICATION_SERVICE_TYPE="ntfy" # or "gotify" or "discord"
# ENV NTFY_SERVER_URL=""
# ENV NTFY_TOPIC=""
# ENV NTFY_ACCESS_TOKEN=""
# ENV NOTIFICATION_PRIORITY="default" # Used by ntfy and mapped for Gotify
# ENV GOTIFY_SERVER_URL=""
# ENV GOTIFY_APP_TOKEN=""
# ENV DISCORD_WEBHOOK_URL=""

EXPOSE 5001

CMD ["python", "app.py"]
