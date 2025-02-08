import json
import os

CONFIG_FILE = "/data/options.json"

DEFAULT_CONFIG = {
    "host_ip": "127.0.0.1",
    "update_interval": 10,      # Aktualisierungsintervall in Minuten
    "notify_on_change": False   # Benachrichtigung bei Statusänderung aktivieren/deaktivieren
}

def load_config():
    """
    Lädt die Konfiguration aus der CONFIG_FILE. Falls die Datei nicht existiert
    oder ein Fehler auftritt, wird DEFAULT_CONFIG zurückgegeben.
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            return config
        except Exception as err:
            print(f"Fehler beim Laden der Konfiguration: {err}")
    return DEFAULT_CONFIG
