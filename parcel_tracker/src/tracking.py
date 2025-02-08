import json
import os
import time
import requests

TRACKINGS_FILE = "/data/trackings.json"
# Global variable where the tracking data is stored
trackings = {}

def load_trackings():
    """
    Loads the tracking data from TRACKINGS_FILE or initializes
    an empty dictionary if the file does not exist or an error occurs.
    """
    global trackings
    if os.path.exists(TRACKINGS_FILE):
        try:
            with open(TRACKINGS_FILE, "r") as f:
                trackings = json.load(f)
        except Exception as err:
            print(f"Error loading tracking data: {err}")
    else:
        trackings = {}

def save_trackings():
    """
    Saves the current tracking data in TRACKINGS_FILE.
    """
    try:
        with open(TRACKINGS_FILE, "w") as f:
            json.dump(trackings, f)
    except Exception as err:
        print(f"Error saving tracking data: {err}")

def dhl_fetch(tracking_number):
    """
    Fetches the DHL tracking information for the given tracking number.
    """
    url = f"https://www.dhl.de/int-verfolgen/data/search?piececode={tracking_number}&language=de"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.dhl.de/int-verfolgen/",
        "Connection": "keep-alive"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        status = "Unknown"
        # Default to the current date if no date is provided
        last_update = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime())
        progress = None
        max_progress = None

        if data.get("sendungen") and isinstance(data["sendungen"], list) and len(data["sendungen"]) > 0:
            sendung = data["sendungen"][0]
            if sendung.get("sendungsdetails") and sendung["sendungsdetails"].get("sendungsverlauf"):
                verlauf = sendung["sendungsdetails"]["sendungsverlauf"]
                status = verlauf.get("aktuellerStatus", status)
                last_update = verlauf.get("datumAktuellerStatus", last_update)
                progress = verlauf.get("fortschritt")
                max_progress = verlauf.get("maximalFortschritt")
        return {
            "status": status,
            "last_update": last_update,
            "progress": progress,
            "maxProgress": max_progress,
            "raw": data
        }
    except Exception as e:
        print(f"Error fetching DHL shipment {tracking_number}: {e}")
        return {
            "status": "Error",
            "last_update": time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()),
            "error": str(e)
        }

def update_trackings(config, send_notification_func):
    """
    Background thread: Periodically updates all tracking data.
    If the status changes and notifications are enabled,
    the send_notification_func is called.
    """
    while True:
        for tn in list(trackings.keys()):
            old_info = trackings.get(tn, {})
            new_info = dhl_fetch(tn)
            # Keep the package name if already set
            if "tracking_name" in old_info:
                new_info["tracking_name"] = old_info["tracking_name"]
            # Send notification on status change if enabled
            if config.get("notify_on_change", False) and old_info.get("status") != new_info.get("status"):
                send_notification_func(
                    tracking_number=tn,
                    old_status=old_info.get("status", "Unbekannt"),
                    new_status=new_info.get("status", "Unbekannt"),
                    tracking_name=new_info.get("tracking_name", "")
                )
            trackings[tn] = new_info
        save_trackings()
        interval = config.get("update_interval", 10)
        time.sleep(interval * 60)
