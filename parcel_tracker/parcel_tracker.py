from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from flask_cors import CORS
import json
import os
import time
import threading
import requests
import logging

# Disable the Werkzeug logger to reduce output from the server
logging.getLogger('werkzeug').disabled = True

# Initialize the Flask application
app = Flask(__name__)

# Enable Cross-Origin Resource Sharing (CORS) for all routes.
# This automatically adds the "Access-Control-Allow-Origin: *" header to all responses.
CORS(app)

# Disable Flask's internal logger for a cleaner output
app.logger.disabled = True

# File paths for configuration and persistent tracking data
CONFIG_FILE = "/data/options.json"     # Home Assistant stores add-on options here
TRACKINGS_FILE = "/data/trackings.json"  # Tracking data is persisted in this file

# Default configuration in case the configuration file doesn't exist or fails to load
DEFAULT_CONFIG = {
    "host_ip": "127.0.0.1",
    "update_interval": 10,      # Update interval in minutes
    "notify_on_change": False   # Whether to send a notification on status change
}

def load_config():
    """
    Loads configuration from the CONFIG_FILE.
    If the file does not exist or cannot be loaded, returns the DEFAULT_CONFIG.
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            return config
        except Exception as err:
            print(f"Error loading configuration: {err}")
    return DEFAULT_CONFIG

# Load the configuration settings
config = load_config()

def load_trackings():
    """
    Loads the tracking data from the TRACKINGS_FILE.
    If the file does not exist or cannot be read, returns an empty dictionary.
    """
    if os.path.exists(TRACKINGS_FILE):
        try:
            with open(TRACKINGS_FILE, "r") as f:
                data = json.load(f)
            return data
        except Exception as err:
            print(f"Error loading tracking data: {err}")
    return {}

def save_trackings():
    """
    Saves the current tracking data to the TRACKINGS_FILE.
    """
    try:
        with open(TRACKINGS_FILE, "w") as f:
            json.dump(trackings, f)
    except Exception as err:
        print(f"Error saving tracking data: {err}")

# Load persisted tracking data
trackings = load_trackings()

def dhl_fetch(tracking_number):
    """
    Fetches tracking information for a given DHL tracking number using the DHL API.
    
    The API is called via:
    https://www.dhl.de/int-verfolgen/data/search?piececode=TRACKING_NUMBER&language=de

    The function extracts:
      - 'aktuellerStatus' (current status)
      - 'datumAktuellerStatus' (date of the current status)
      - Optionally, 'fortschritt' (progress) and 'maximalFortschritt' (maximum progress)

    Returns a dictionary with the following keys:
      - status
      - last_update
      - progress
      - maxProgress
      - raw: the complete JSON response from the API
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
        # Default last update is set to the current time if not provided
        last_update = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime())
        progress = None
        max_progress = None

        # Check if the API response contains a list of shipments ("sendungen")
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

def send_notification(tracking_number, old_status, new_status, tracking_name=""):
    """
    Sends a persistent notification to Home Assistant via its REST API.
    
    Parameters:
      - tracking_number: The DHL tracking number.
      - old_status: The previous status of the shipment.
      - new_status: The new status of the shipment.
      - tracking_name: An optional package name.
    
    Requires the environment variable HASSIO_TOKEN to be set.
    """
    hass_url = os.environ.get("HASS_URL", f"http://{config.get('host_ip', '127.0.0.1')}:8123")
    token = os.environ.get("HASSIO_TOKEN")
    if not token:
        print("No HASSIO_TOKEN found, notification will not be sent.")
        return
    url = f"{hass_url}/api/services/persistent_notification/create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    # Use the tracking_name if provided; otherwise, fall back to the tracking_number
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

def update_trackings():
    """
    Background thread function that periodically updates the tracking information for all shipments.
    
    For each tracking number in the 'trackings' dictionary, it fetches the latest information
    from DHL. If a package name already exists, it is preserved. If the status has changed and
    notify_on_change is enabled in the configuration, a notification is sent via send_notification.
    
    The update interval is determined by the 'update_interval' setting from the configuration (in minutes).
    """
    while True:
        for tn in list(trackings.keys()):
            old_info = trackings.get(tn, {})
            new_info = dhl_fetch(tn)
            # Preserve the package name if it has already been set
            if "tracking_name" in old_info:
                new_info["tracking_name"] = old_info["tracking_name"]
            # If notifications are enabled and the status has changed, send a notification
            if config.get("notify_on_change", False) and old_info.get("status") != new_info.get("status"):
                send_notification(
                    tracking_number=tn,
                    old_status=old_info.get("status", "Unbekannt"),
                    new_status=new_info.get("status", "Unbekannt"),
                    tracking_name=new_info.get("tracking_name", "")
                )
            trackings[tn] = new_info
        save_trackings()
        interval = config.get("update_interval", 10)
        time.sleep(interval * 60)

# HTML template for the overview page, utilizing Vue.js for dynamic updates
TEMPLATE = '''
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Parcel Tracker Übersicht</title>
  <!-- Include Tailwind CSS from CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- Include Vue.js (Vue 3) from CDN -->
  <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
  <script>
    // Enable dark mode if preferred by the user's system
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.classList.add('dark');
    }
  </script>
  <style>
    /* Dark, elegant glass effect with a subtle white border */
    .glass-box {
      background: rgba(0, 0, 0, 0.8); /* 80% opacity */
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 0.5rem;
    }
    /* Logo hover effect: slight rotation, scale down, and partial transparency */
    .logo-hover {
      transition: transform 300ms ease, opacity 300ms ease;
    }
    .logo-hover:hover {
      transform: rotate(-5deg) scale(0.9);
      opacity: 0.5;
    }
  </style>
</head>
<body class="bg-black text-white">
  <!-- Vue application container -->
  <div id="app" class="min-h-screen flex items-center justify-center p-4">
    <!-- Container with a maximum width for consistent layout -->
    <div class="w-full max-w-4xl space-y-8">
      <!-- Logo with hover effect -->
      <div class="flex justify-center">
        <img src="https://raw.githubusercontent.com/nils-kt/nils-kt-addons/refs/heads/main/parcel_tracker/icon.png" 
             alt="Parcel Tracker Logo" 
             class="logo-hover w-32 h-auto">
      </div>
      <h1 class="text-4xl font-bold text-center">Parcel Tracker Übersicht</h1>
      
      <!-- Form for adding a new tracking number -->
      <div class="glass-box w-full p-6 shadow-xl">
        <h2 class="text-2xl font-semibold mb-4">Add Tracking Number</h2>
        <!-- The form includes fields for the tracking number and an optional package name -->
        <form action="{{ url_for('add_tracking_form') }}" method="post" class="flex flex-col sm:flex-row gap-4">
          <input type="text" id="tracking_number" name="tracking_number" placeholder="Tracking Number" required
                 class="flex-1 p-3 border border-gray-700 rounded bg-black text-white focus:outline-none focus:ring-2 focus:ring-blue-400">
          <input type="text" id="package_name" name="package_name" placeholder="Package Name (optional)"
                 class="flex-1 p-3 border border-gray-700 rounded bg-black text-white focus:outline-none focus:ring-2 focus:ring-blue-400">
          <button type="submit" class="px-6 py-3 rounded bg-gray-700 hover:bg-gray-600 text-white font-bold shadow focus:outline-none focus:ring-2 focus:ring-blue-400">
            Add
          </button>
        </form>
      </div>
      
      <!-- Table displaying the active shipments -->
      <div class="glass-box w-full p-6 shadow-xl">
        <h2 class="text-2xl font-semibold mb-4">Active Shipments</h2>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-separate" style="border-spacing: 0">
            <thead>
              <tr class="bg-black">
                <th class="px-4 py-2 border-b border-gray-700">Name</th>
                <th class="px-4 py-2 border-b border-gray-700">Status</th>
                <th class="px-4 py-2 border-b border-gray-700">Progress</th>
                <th class="px-4 py-2 border-b border-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody>
            {% raw %}
              <tr v-if="trackings.length === 0">
                <td colspan="4" class="px-4 py-2 text-center">No shipments available.</td>
              </tr>
              <tr v-for="item in trackings" :key="item.tracking_number" class="transition-colors duration-300 hover:bg-white/10">
                <td class="px-4 py-2 border-b border-gray-700">
                  {{ item.tracking_name ? (item.tracking_name + ' (' + item.tracking_number + ')') : item.tracking_number }}
                </td>
                <td class="px-4 py-2 border-b border-gray-700">{{ item.status }}</td>
                <td class="px-4 py-2 border-b border-gray-700">
                  {{ (item.progress !== null && item.maxProgress !== null) ? (item.progress + ' / ' + item.maxProgress) : '-' }}
                </td>
                <td class="px-4 py-2 border-b border-gray-700">
                  <button @click="deleteTracking(item.tracking_number)" class="px-3 py-1 rounded bg-red-700 hover:bg-red-600 text-white font-semibold focus:outline-none focus:ring-2 focus:ring-red-400">
                    Delete
                  </button>
                </td>
              </tr>
            {% endraw %}
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- Footer section -->
      <footer class="text-center text-sm text-gray-500">
        <p>Created with ♥️ by <a href="https://github.com/nils-kt/nils-kt-addons" target="_blank" class="hover:underline">nils-kt</a></p>
      </footer>
    </div>
  </div>
  
  <!-- Vue application script -->
  <script>
    // Convert update_interval (in minutes) from the configuration to milliseconds
    const updateInterval = {{ config.update_interval|int * 60000 }};
    
    const app = Vue.createApp({
      data() {
        return {
          trackings: []  // Array to store the tracking data
        }
      },
      methods: {
        // Fetch tracking data from the server endpoint
        fetchTrackings() {
          fetch("/trackings")
            .then(response => response.json())
            .then(data => {
              this.trackings = data;
            })
            .catch(error => {
              console.error("Error fetching shipments:", error);
            });
        },
        // Delete a specific tracking entry by sending a POST request
        deleteTracking(tracking_number) {
          fetch("/delete/" + encodeURIComponent(tracking_number), { method: "POST" })
            .then(response => {
              if (response.ok) {
                this.fetchTrackings();
              } else {
                console.error("Error deleting shipment:", tracking_number);
              }
            })
            .catch(error => {
              console.error("Error deleting shipment:", error);
            });
        }
      },
      mounted() {
        // Fetch the tracking data as soon as the Vue app is mounted
        this.fetchTrackings();
        // Set up an interval to periodically fetch updated tracking data
        setInterval(this.fetchTrackings, updateInterval);
      }
    });
    
    // Mount the Vue app to the DOM element with id="app"
    app.mount("#app");
  </script>
</body>
</html>
'''

@app.route("/", methods=["GET"])
def overview():
    """
    Renders the overview page using the HTML template.
    Passes the current tracking data and configuration settings to the template.
    """
    return render_template_string(TEMPLATE, trackings=trackings, config=config)

@app.route("/trackings", methods=["GET"])
def get_trackings():
    """
    Returns a JSON response containing the current tracking data.
    Formats the 'last_update' timestamp for better readability.
    """
    results = []
    for tn, info in trackings.items():
        last_update_str = info.get("last_update", "")
        try:
            # Attempt to parse the timestamp in different formats
            try:
                last_update_timestamp = int(time.mktime(time.strptime(last_update_str, "%d.%m.%Y %H:%M:%S")))
            except ValueError:
                last_update_timestamp = int(time.mktime(time.strptime(last_update_str, "%Y-%m-%dT%H:%M:%S%z")))
        except ValueError:
            last_update_timestamp = None
        if last_update_timestamp:
            last_update_str = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(last_update_timestamp))
        results.append({
            "tracking_number": tn,
            "tracking_name": info.get("tracking_name", ""),
            "status": info.get("status", "unknown"),
            "last_update": last_update_str,
            "last_update_timestamp": last_update_timestamp,
            "progress": info.get("progress"),
            "maxProgress": info.get("maxProgress")
        })
    return jsonify(results)

@app.route("/add", methods=["POST"])
def add_tracking_form():
    """
    Adds a new tracking number to the tracking data.
    Retrieves the tracking number and package name from the POST data.
    If the tracking number is missing or already exists, redirects to the overview.
    Otherwise, it fetches the tracking details from DHL, stores them, and then redirects.
    """
    tn = request.form.get("tracking_number")
    package_name = request.form.get("package_name")
    if not tn:
        return redirect(url_for("overview"))
    if tn in trackings:
        return redirect(url_for("overview"))
    new_info = dhl_fetch(tn)
    new_info["tracking_name"] = package_name if package_name else ""
    trackings[tn] = new_info
    save_trackings()
    return redirect(url_for("overview"))

@app.route("/delete/<tracking_number>", methods=["POST"])
def delete_tracking_form(tracking_number):
    """
    Deletes a tracking entry based on the provided tracking number.
    After deletion, saves the updated tracking data and redirects to the overview.
    """
    if tracking_number in trackings:
        del trackings[tracking_number]
    save_trackings()
    return redirect(url_for("overview"))

if __name__ == "__main__":
    # Start a background thread to periodically update tracking data.
    updater = threading.Thread(target=update_trackings, daemon=True)
    updater.start()
    # Run the Flask application on host 0.0.0.0 and port 58784
    app.run(host="0.0.0.0", port=58784)

@app.after_request
def add_cors_headers(response):
    """
    Adds CORS headers to every HTTP response.
    Allows any origin and specific headers and methods.
    """
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response
