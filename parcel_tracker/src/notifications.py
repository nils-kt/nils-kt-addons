import os
import requests

def send_notification(tracking_number, old_status, new_status, tracking_name=""):
    """
    Sends a notification to Home Assistant.
    It uses HASS_URL and HASSIO_TOKEN from the environment variables.
    """
    hass_url = os.environ.get("HASS_URL", f"http://{os.environ.get('host_ip', '127.0.0.1')}:8123")
    token = os.environ.get("HASSIO_TOKEN")
    if not token:
        print("No HASSIO_TOKEN found, notification will not be sent.")
        return
    url = f"{hass_url}/api/services/persistent_notification/create"
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
        print(f"Notification sent for {tracking_number}")
    except Exception as e:
        print(f"Error sending notification for {tracking_number}: {e}")
