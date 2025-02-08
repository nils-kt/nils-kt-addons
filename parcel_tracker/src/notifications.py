import os
import requests

def send_notification(tracking_number, old_status, new_status, tracking_name=""):
    """
    Versendet eine Benachrichtigung an Home Assistant.
    Dafür werden HASS_URL und HASSIO_TOKEN aus den Umgebungsvariablen verwendet.
    """
    hass_url = os.environ.get("HASS_URL", f"http://{os.environ.get('host_ip', '127.0.0.1')}:8123")
    token = os.environ.get("HASSIO_TOKEN")
    if not token:
        print("Kein HASSIO_TOKEN gefunden, Benachrichtigung wird nicht gesendet.")
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
        print(f"Benachrichtigung gesendet für {tracking_number}")
    except Exception as e:
        print(f"Fehler beim Senden der Benachrichtigung für {tracking_number}: {e}")
