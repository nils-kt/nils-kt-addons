from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from flask_cors import CORS
import json
import os
import time
import threading
import requests

app = Flask(__name__)
CORS(app)  # Fügt automatisch den Header "Access-Control-Allow-Origin: *" zu allen Antworten hinzu.

# Globaler Speicher für Sendungen
# Schlüssel: Tracking-Nummer, Wert: Dictionary mit Statusinformationen + optionaler Name
trackings = {}

# Konfiguration: Standardwerte werden aus der Add‑On-Konfiguration geladen
CONFIG_FILE = "/data/options.json"  # Home Assistant speichert die Add‑On-Optionen hier
DEFAULT_CONFIG = {
    "host_ip": "127.0.0.1",
    "update_interval": 10,      # in Minuten
    "notify_on_change": False
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            return config
        except Exception as err:
            print(f"Fehler beim Laden der Konfiguration: {err}")
    return DEFAULT_CONFIG

config = load_config()

# HTML-Template für die Übersichtsseite (mit Vue.js)
TEMPLATE = '''
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Parcel Tracker Übersicht</title>
  <!-- Tailwind CSS via CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- Vue.js via CDN (Vue 3) -->
  <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
  <script>
    // Falls der Dark Mode vom Betriebssystem bevorzugt wird, füge die Klasse "dark" hinzu
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.classList.add('dark');
    }
  </script>
  <style>
    /* Dunkler, eleganter Glass-Effekt mit kleinem weißen Border */
    .glass-box {
      background: rgba(0, 0, 0, 0.8); /* 80% opak */
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 0.5rem;
    }
    /* Logo-Hover-Effekt: leicht drehen, verkleinern und halbtransparent */
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
  <!-- Vue App Container -->
  <div id="app" class="min-h-screen flex items-center justify-center p-4">
    <!-- Container mit gleicher max-width für beide Boxen -->
    <div class="w-full max-w-4xl space-y-8">
      <!-- Logo oberhalb der Überschrift mit Hover-Effekt -->
      <div class="flex justify-center">
        <img src="https://raw.githubusercontent.com/nils-kt/nils-kt-addons/refs/heads/main/parcel_tracker/icon.png" 
             alt="Parcel Tracker Logo" 
             class="logo-hover w-32 h-auto">
      </div>
      <h1 class="text-4xl font-bold text-center">Parcel Tracker Übersicht</h1>
      
      <!-- Formular-Box: gleiche Breite wie die Tabelle -->
      <div class="glass-box w-full p-6 shadow-xl">
        <h2 class="text-2xl font-semibold mb-4">Trackingnummer hinzufügen</h2>
        <!-- Formular mit zwei Feldern: Trackingnummer und Paketname -->
        <form action="{{ url_for('add_tracking_form') }}" method="post" class="flex flex-col sm:flex-row gap-4">
          <input type="text" id="tracking_number" name="tracking_number" placeholder="Trackingnummer" required
                 class="flex-1 p-3 border border-gray-700 rounded bg-black text-white focus:outline-none focus:ring-2 focus:ring-blue-400">
          <input type="text" id="package_name" name="package_name" placeholder="Paketname (optional)"
                 class="flex-1 p-3 border border-gray-700 rounded bg-black text-white focus:outline-none focus:ring-2 focus:ring-blue-400">
          <button type="submit" class="px-6 py-3 rounded bg-gray-700 hover:bg-gray-600 text-white font-bold shadow focus:outline-none focus:ring-2 focus:ring-blue-400">
            Hinzufügen
          </button>
        </form>
      </div>
      
      <!-- Tabelle-Box: gleiche Breite -->
      <div class="glass-box w-full p-6 shadow-xl">
        <h2 class="text-2xl font-semibold mb-4">Aktive Sendungen</h2>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-separate" style="border-spacing: 0">
            <thead>
              <tr class="bg-black">
                <th class="px-4 py-2 border-b border-gray-700">Sendungsnummer</th>
                <th class="px-4 py-2 border-b border-gray-700">Name</th>
                <th class="px-4 py-2 border-b border-gray-700">Status</th>
                <th class="px-4 py-2 border-b border-gray-700">Letzte Aktualisierung</th>
                <th class="px-4 py-2 border-b border-gray-700">Aktionen</th>
              </tr>
            </thead>
            <tbody>
            {% raw %}
              <!-- Falls keine Daten vorhanden sind -->
              <tr v-if="trackings.length === 0">
                <td colspan="5" class="px-4 py-2 text-center">Keine Sendungen vorhanden.</td>
              </tr>
              <!-- Dynamische Zeilen über v-for -->
              <tr v-for="item in trackings" :key="item.tracking_number" class="transition-colors duration-300 hover:bg-white/10">
                <td class="px-4 py-2 border-b border-gray-700">{{ item.tracking_number }}</td>
                <td class="px-4 py-2 border-b border-gray-700">{{ item.tracking_name }}</td>
                <td class="px-4 py-2 border-b border-gray-700">{{ item.status }}</td>
                <td class="px-4 py-2 border-b border-gray-700">{{ item.last_update }}</td>
                <td class="px-4 py-2 border-b border-gray-700">
                  <button @click="deleteTracking(item.tracking_number)" class="px-3 py-1 rounded bg-red-700 hover:bg-red-600 text-white font-semibold focus:outline-none focus:ring-2 focus:ring-red-400">
                    Löschen
                  </button>
                </td>
              </tr>
            {% endraw %}
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- Footer -->
      <footer class="text-center text-sm text-gray-500">
        <p>Created with ♥️ by <a href="https://github.com/nils-kt/nils-kt-addons" target="_blank" class="hover:underline">nils-kt</a></p>
      </footer>
    </div>
  </div>
  
  <!-- Vue App Script -->
  <script>
    // Der update_interval-Wert (in Minuten) aus der Konfiguration wird in Millisekunden umgerechnet.
    const updateInterval = {{ config.update_interval|int * 60000 }};
    
    const app = Vue.createApp({
      data() {
        return {
          trackings: []
        }
      },
      methods: {
        fetchTrackings() {
          fetch("/trackings")
            .then(response => response.json())
            .then(data => {
              this.trackings = data;
            })
            .catch(error => {
              console.error("Fehler beim Abrufen der Sendungen:", error);
            });
        },
        deleteTracking(tracking_number) {
          fetch("/delete/" + encodeURIComponent(tracking_number), { method: "POST" })
            .then(response => {
              if (response.ok) {
                this.fetchTrackings();
              } else {
                console.error("Fehler beim Löschen der Sendung:", tracking_number);
              }
            })
            .catch(error => {
              console.error("Fehler beim Löschen der Sendung:", error);
            });
        }
      },
      mounted() {
        this.fetchTrackings();
        setInterval(this.fetchTrackings, updateInterval);
      }
    });
    
    app.mount("#app");
  </script>
</body>
</html>
'''

def dhl_fetch(tracking_number):
    """
    Fragt die DHL-API für eine Trackingnummer ab.
    Die API wird über den folgenden URL aufgerufen:
    https://www.dhl.de/int-verfolgen/data/search?piececode=SENDUNGSNUMMER&language=de

    Die Funktion extrahiert den 'aktuellerStatus' und 'datumAktuellerStatus'
    aus der Antwort.
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
        status = "Unbekannt"
        last_update = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime())
        if data.get("sendungen") and isinstance(data["sendungen"], list) and len(data["sendungen"]) > 0:
            sendung = data["sendungen"][0]
            if sendung.get("sendungsdetails") and sendung["sendungsdetails"].get("sendungsverlauf"):
                verlauf = sendung["sendungsdetails"]["sendungsverlauf"]
                status = verlauf.get("aktuellerStatus", status)
                last_update = verlauf.get("datumAktuellerStatus", last_update)
        return {"status": status, "last_update": last_update, "raw": data}
    except Exception as e:
        print(f"Fehler beim Abrufen der DHL-Sendung {tracking_number}: {e}")
        return {"status": "Fehler", "last_update": time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()), "error": str(e)}

def send_notification(tracking_number, old_status, new_status):
    """Sendet eine persistent_notification an Home Assistant über die REST-API."""
    # Verwende HASS_URL aus der Umgebung oder setze einen Standardwert
    hass_url = os.environ.get("HASS_URL", f"http://{config.get('host_ip', '127.0.0.1')}:8123")
    token = os.environ.get("HASSIO_TOKEN")
    if not token:
        print("Kein HASSIO_TOKEN gefunden, Benachrichtigung wird nicht gesendet.")
        return
    url = f"{hass_url}/api/services/persistent_notification/create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "title": "Parcel Tracker",
        "message": f"Statusänderung für {tracking_number}: {old_status} → {new_status}"
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print(f"Benachrichtigung gesendet für {tracking_number}")
    except Exception as e:
        print(f"Fehler beim Senden der Benachrichtigung für {tracking_number}: {e}")

def update_trackings():
    """Hintergrundthread, der alle Sendungen in regelmäßigen Abständen aktualisiert."""
    while True:
        for tn in list(trackings.keys()):
            # Hole neue Infos
            new_info = dhl_fetch(tn)
            # Erhalte den alten Paketnamen, falls vorhanden, und behalte ihn
            if "tracking_name" in trackings[tn]:
                new_info["tracking_name"] = trackings[tn]["tracking_name"]
            trackings[tn] = new_info
        interval = config.get("update_interval", 10)
        time.sleep(interval * 60)

@app.route("/", methods=["GET"])
def overview():
    return render_template_string(TEMPLATE, trackings=trackings, config=config)

@app.route("/trackings", methods=["GET"])
def get_trackings():
    """Gibt alle aktiven Sendungen als JSON zurück."""
    results = []
    for tn, info in trackings.items():
        last_update_str = info.get("last_update", "")
        try:
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
            "tracking_name": info.get("tracking_name", ""),  # Paketname hinzufügen
            "status": info.get("status", "unbekannt"),
            "last_update": last_update_str,
            "last_update_timestamp": last_update_timestamp
        })
    return jsonify(results)

@app.route("/add", methods=["POST"])
def add_tracking_form():
    """Verarbeitet das Formular zum Hinzufügen einer Trackingnummer."""
    tn = request.form.get("tracking_number")
    package_name = request.form.get("package_name")  # Neues Feld für den Paketnamen
    if not tn:
        return redirect(url_for("overview"))
    if tn in trackings:
        return redirect(url_for("overview"))
    new_info = dhl_fetch(tn)
    new_info["tracking_name"] = package_name if package_name else ""
    trackings[tn] = new_info
    return redirect(url_for("overview"))

@app.route("/delete/<tracking_number>", methods=["POST"])
def delete_tracking_form(tracking_number):
    """Verarbeitet das Löschen einer Trackingnummer über das Formular."""
    if tracking_number in trackings:
        del trackings[tracking_number]
    return redirect(url_for("overview"))

if __name__ == "__main__":
    # Starte den Hintergrundthread zur Aktualisierung der Sendungen
    updater = threading.Thread(target=update_trackings, daemon=True)
    updater.start()
    # Starte den Flask-Webserver
    app.run(host="0.0.0.0", port=58784)

@app.after_request
def add_cors_headers(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response
