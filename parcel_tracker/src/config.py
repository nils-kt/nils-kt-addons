import json
import os

CONFIG_FILE = "/data/options.json"

DEFAULT_CONFIG = {
    "host_ip": "127.0.0.1",
    "update_interval": 10,      # Update interval in minutes
    "notify_on_change": False   # Enable/disable notification on status change
}

def load_config():
    """
    Loads the configuration from CONFIG_FILE. If the file does not exist
    or an error occurs, DEFAULT_CONFIG is returned.
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            return config
        except Exception as err:
            print(f"Error loading configuration: {err}")
    return DEFAULT_CONFIG
