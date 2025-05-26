from flask import Flask, request, jsonify
import requests
import json
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# --- General Configuration ---
NOTIFICATION_SERVICE_TYPE = os.environ.get('NOTIFICATION_SERVICE_TYPE', 'ntfy').lower() # 'ntfy', 'gotify', or 'discord'
NOTIFICATION_PRIORITY_GENERAL = os.environ.get('NOTIFICATION_PRIORITY', 'default') # For ntfy and to be mapped for Gotify

# --- ntfy Configuration ---
NTFY_SERVER_URL = os.environ.get('NTFY_SERVER_URL')
NTFY_TOPIC = os.environ.get('NTFY_TOPIC')
NTFY_ACCESS_TOKEN = os.environ.get('NTFY_ACCESS_TOKEN')

# --- Gotify Configuration ---
GOTIFY_SERVER_URL = os.environ.get('GOTIFY_SERVER_URL') # e.g., http://gotify.example.com
GOTIFY_APP_TOKEN = os.environ.get('GOTIFY_APP_TOKEN')  # Token for your Gotify application

# --- Discord Configuration ---
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

# --- Helper function to map general priority to Gotify's numeric priority ---
def map_priority_to_gotify(priority_str):
    mapping = {
        "min": 1,
        "low": 3,
        "default": 5,
        "high": 8,
        "max": 10
    }
    return mapping.get(priority_str.lower(), 5) # Default to 5 if not found

# --- Notification Sending Functions ---

def send_ntfy_notification(title, message_lines, manifest_url, priority):
    if not NTFY_SERVER_URL or not NTFY_TOPIC:
        app.logger.error("Ntfy not configured (NTFY_SERVER_URL or NTFY_TOPIC missing).")
        return False

    full_message = "\n".join(message_lines)
    app.logger.info(f"Preparing ntfy notification: Title='{title}', Message='{full_message}'")

    headers = {
        "Title": title.encode('utf-8'),
        "Priority": priority
    }
    if NTFY_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {NTFY_ACCESS_TOKEN}"
    if manifest_url:
        headers["Click"] = f"view, {manifest_url}, Open Manifest URL"
        # headers["Actions"] = f"view, Open Manifest, {manifest_url}" # Alternative action

    try:
        response = requests.post(
            f"{NTFY_SERVER_URL.rstrip('/')}/{NTFY_TOPIC}",
            data=full_message.encode('utf-8'),
            headers=headers
        )
        response.raise_for_status()
        app.logger.info(f"Notification sent to ntfy. Status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error sending notification to ntfy: {e}")
        if hasattr(e, 'response') and e.response is not None:
            app.logger.error(f"ntfy response content: {e.response.text}")
        return False

def send_gotify_notification(title, message_lines, manifest_url, priority_str):
    if not GOTIFY_SERVER_URL or not GOTIFY_APP_TOKEN:
        app.logger.error("Gotify not configured (GOTIFY_SERVER_URL or GOTIFY_APP_TOKEN missing).")
        return False

    full_message = "\n".join(message_lines)
    if manifest_url:
        full_message += f"\n\nManifest: {manifest_url}" # Gotify typically uses Markdown in messages

    app.logger.info(f"Preparing Gotify notification: Title='{title}', Message='{full_message}'")

    gotify_priority = map_priority_to_gotify(priority_str)
    payload = {
        "title": title,
        "message": full_message,
        "priority": gotify_priority,
    }
    if manifest_url: # Add clickable link if Gotify client supports it
        payload["extras"] = {
            "client::notification": {
                "click": {"url": manifest_url}
            }
        }


    headers = {
        "X-Gotify-Key": GOTIFY_APP_TOKEN,
        "Content-Type": "application/json"
    }
    # Alternative: send token as query param: f"{GOTIFY_SERVER_URL.rstrip('/')}/message?token={GOTIFY_APP_TOKEN}"

    try:
        response = requests.post(
            f"{GOTIFY_SERVER_URL.rstrip('/')}/message",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        app.logger.info(f"Notification sent to Gotify. Status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error sending notification to Gotify: {e}")
        if hasattr(e, 'response') and e.response is not None:
            app.logger.error(f"Gotify response content: {e.response.text}")
        return False

def send_discord_notification(title, message_lines, repository, tag, actor_name, digest, manifest_url):
    if not DISCORD_WEBHOOK_URL:
        app.logger.error("Discord not configured (DISCORD_WEBHOOK_URL missing).")
        return False

    # Construct a Discord embed
    embed = {
        "title": title,
        "color": 0x0099FF, # Blue color, you can change this
        "fields": []
    }
    if repository:
        embed["fields"].append({"name": "Repository", "value": repository, "inline": True})
    if tag:
        embed["fields"].append({"name": "Tag", "value": tag, "inline": True})
    if actor_name:
        embed["fields"].append({"name": "Pushed by", "value": actor_name, "inline": True})
    if digest:
        embed["fields"].append({"name": "Digest", "value": f"{digest[:12]}...", "inline": True})

    description_parts = [line for line in message_lines if not (line.startswith("Repository:") or line.startswith("Tag:") or line.startswith("Pushed by:") or line.startswith("Digest:"))]
    embed["description"] = "\n".join(description_parts)


    if manifest_url:
        embed["fields"].append({"name": "Manifest URL", "value": f"[Link]({manifest_url})", "inline": False})
        # You could also make the title a link if preferred:
        # embed["url"] = manifest_url

    payload = {
        "username": "Registry Notifier", # You can customize this
        # "content": f"**{title}**", # Optional: for a simple message above the embed
        "embeds": [embed]
    }

    app.logger.info(f"Preparing Discord notification: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        app.logger.info(f"Notification sent to Discord. Status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error sending notification to Discord: {e}")
        if hasattr(e, 'response') and e.response is not None:
            app.logger.error(f"Discord response content: {e.response.text}")
            app.logger.error(f"Discord response headers: {e.response.headers}")
        return False


@app.route('/notify', methods=['POST'])
def registry_notification_handler():
    if NOTIFICATION_SERVICE_TYPE == 'ntfy' and (not NTFY_SERVER_URL or not NTFY_TOPIC):
        app.logger.error("Ntfy service selected but not configured.")
        return jsonify({"status": "error", "message": "Receiver (ntfy) not configured"}), 500
    elif NOTIFICATION_SERVICE_TYPE == 'gotify' and (not GOTIFY_SERVER_URL or not GOTIFY_APP_TOKEN):
        app.logger.error("Gotify service selected but not configured.")
        return jsonify({"status": "error", "message": "Receiver (Gotify) not configured"}), 500
    elif NOTIFICATION_SERVICE_TYPE == 'discord' and not DISCORD_WEBHOOK_URL:
        app.logger.error("Discord service selected but not configured.")
        return jsonify({"status": "error", "message": "Receiver (Discord) not configured"}), 500
    elif NOTIFICATION_SERVICE_TYPE not in ['ntfy', 'gotify', 'discord']:
        app.logger.error(f"Invalid NOTIFICATION_SERVICE_TYPE: {NOTIFICATION_SERVICE_TYPE}")
        return jsonify({"status": "error", "message": "Invalid notification service type configured"}), 500

    if not request.is_json:
        app.logger.warning("Received non-JSON request")
        return jsonify({"status": "error", "message": "Request was not JSON"}), 400

    data = request.get_json()
    app.logger.info(f"Received registry webhook: {json.dumps(data, indent=2)}")

    if data.get('events'):
        for event in data['events']:
            action = event.get('action')
            target = event.get('target', {})
            repository = target.get('repository')
            tag = target.get('tag')
            actor_name = event.get('actor', {}).get('name')
            digest = target.get('digest')
            manifest_url = target.get('url')

            if action == 'push' and repository:
                title = f"Image Pushed: {repository}"
                if tag:
                    title += f":{tag}"

                message_lines = []
                if tag:
                    message_lines.append(f"Tag: {tag}")
                message_lines.append(f"Repository: {repository}")
                if actor_name:
                    message_lines.append(f"Pushed by: {actor_name}")
                if digest:
                    message_lines.append(f"Digest: {digest[:12]}...")

                # Dispatch to the appropriate notification service
                if NOTIFICATION_SERVICE_TYPE == 'ntfy':
                    send_ntfy_notification(title, message_lines, manifest_url, NOTIFICATION_PRIORITY_GENERAL)
                elif NOTIFICATION_SERVICE_TYPE == 'gotify':
                    send_gotify_notification(title, message_lines, manifest_url, NOTIFICATION_PRIORITY_GENERAL)
                elif NOTIFICATION_SERVICE_TYPE == 'discord':
                    # Discord function takes more granular data for better embed formatting
                    send_discord_notification(title, message_lines, repository, tag, actor_name, digest, manifest_url)
    else:
        app.logger.info("Webhook received, but no events to process.")


    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    service_configured = False
    if NOTIFICATION_SERVICE_TYPE == 'ntfy':
        if NTFY_SERVER_URL and NTFY_TOPIC:
            app.logger.info(f"Ntfy service configured. Notifications will be sent to: {NTFY_SERVER_URL.rstrip('/')}/{NTFY_TOPIC}")
            service_configured = True
        else:
            app.logger.error("FATAL: Ntfy is the selected service, but NTFY_SERVER_URL or NTFY_TOPIC environment variables are not set.")
    elif NOTIFICATION_SERVICE_TYPE == 'gotify':
        if GOTIFY_SERVER_URL and GOTIFY_APP_TOKEN:
            app.logger.info(f"Gotify service configured. Notifications will be sent to: {GOTIFY_SERVER_URL.rstrip('/')}")
            service_configured = True
        else:
            app.logger.error("FATAL: Gotify is the selected service, but GOTIFY_SERVER_URL or GOTIFY_APP_TOKEN environment variables are not set.")
    elif NOTIFICATION_SERVICE_TYPE == 'discord':
        if DISCORD_WEBHOOK_URL:
            app.logger.info(f"Discord service configured. Notifications will be sent via webhook.")
            service_configured = True
        else:
            app.logger.error("FATAL: Discord is the selected service, but DISCORD_WEBHOOK_URL environment variable is not set.")
    else:
        app.logger.error(f"FATAL: Invalid NOTIFICATION_SERVICE_TYPE '{NOTIFICATION_SERVICE_TYPE}' configured. Choose 'ntfy', 'gotify', or 'discord'.")

    if not service_configured:
        exit(1)

    app.logger.info(f"Webhook receiver starting. Active notification service: {NOTIFICATION_SERVICE_TYPE.upper()}")
    app.run(host='0.0.0.0', port=5001, debug=False)
