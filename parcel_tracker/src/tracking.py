import json
import os
import time
import requests

TRACKINGS_FILE = "/data/trackings.json"
# Globale Variable, in der die Tracking-Daten gespeichert werden
trackings = {}

def load_trackings():
    """
    Lädt die Tracking-Daten aus der TRACKINGS_FILE oder initialisiert
    ein leeres Dictionary, falls die Datei nicht existiert oder ein Fehler auftritt.
    """
    global trackings
    if os.path.exists(TRACKINGS_FILE):
        try:
            with open(TRACKINGS_FILE, "r") as f:
                trackings = json.load(f)
        except Exception as err:
            print(f"Fehler beim Laden der Trackings: {err}")
    else:
        trackings = {}

def save_trackings():
    """
    Speichert die aktuellen Tracking-Daten in der TRACKINGS_FILE.
    """
    try:
        with open(TRACKINGS_FILE, "w") as f:
            json.dump(trackings, f)
    except Exception as err:
        print(f"Fehler beim Speichern der Trackings: {err}")

def dhl_fetch(tracking_number):
    """
    Ruft die Sendungsverfolgung von DHL für die übergebene Tracking-Nummer ab.
    """
    url = f"https://www.dhl.de/int-verfolgen/data/search?piececode={tracking_number}&language=de"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, wie Gecko) Chrome/115.0.0.0 Safari/537.36",
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
        # Standardmäßig aktuelles Datum, falls kein Datum geliefert wird
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
        print(f"Fehler beim Abrufen der DHL Sendung {tracking_number}: {e}")
        return {
            "status": "Error",
            "last_update": time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()),
            "error": str(e)
        }

def update_trackings(config, send_notification_func):
    """
    Hintergrund-Thread: Aktualisiert periodisch alle Tracking-Daten.
    Wenn der Status sich ändert und Benachrichtigungen aktiviert sind,
    wird die send_notification_func aufgerufen.
    """
    while True:
        for tn in list(trackings.keys()):
            old_info = trackings.get(tn, {})
            new_info = dhl_fetch(tn)
            # Behalte den Paketnamen, falls bereits gesetzt
            if "tracking_name" in old_info:
                new_info["tracking_name"] = old_info["tracking_name"]
            # Sende Benachrichtigung bei Statusänderung, wenn aktiviert
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
