import os
import logging
import requests

logger = logging.getLogger(__name__)

def send_notification(tracking_number, old_status, new_status, tracking_name=""):
    """
    Sends a notification to Home Assistant using the Supervisor API endpoint.
    Uses the SUPERVISOR_TOKEN from environment variables.
    
    The API endpoint is fixed to "http://supervisor/core/api", so that communication
    is done with the Supervisor rather than directly with the Core.
    """
    supervisor_url = "http://supervisor/core/api"
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        logger.error("No SUPERVISOR_TOKEN found, notification will not be sent.")
        return

    # Debug output: show last 4 characters of the token (without exposing the full token)
    logger.debug(f"Using SUPERVISOR_TOKEN ending with: {token[-4:]}")

    url = f"{supervisor_url}/services/persistent_notification/create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    display_name = tracking_name if tracking_name else tracking_number
    payload = {
        "title": "Parcel Tracker",
        "message": f"Änderung für {display_name}: {old_status} → {new_status}"
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Notification sent for {tracking_number}")
    except Exception as e:
        logger.error(f"Error sending notification for {tracking_number}: {e}")
