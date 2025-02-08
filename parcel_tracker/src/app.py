from flask import Flask
from flask_cors import CORS
import threading
import logging
from parcel_tracker.src.config import load_config
from parcel_tracker.src.tracking import load_trackings, update_trackings, trackings
from parcel_tracker.src.notifications import send_notification
from parcel_tracker.src.routes import bp as routes_bp

# Deaktiviere den Werkzeug-Logger für eine saubere Ausgabe
logging.getLogger('werkzeug').disabled = True

app = Flask(__name__)
CORS(app)
app.logger.disabled = True

# Lade Konfiguration und Trackings
config = load_config()
load_trackings()

# Registriere den Blueprint mit den Routen
app.register_blueprint(routes_bp)

@app.after_request
def add_cors_headers(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response

if __name__ == "__main__":
    # Starte den Hintergrund-Thread für die Aktualisierung der Tracking-Daten
    updater = threading.Thread(target=update_trackings, args=(config, send_notification), daemon=True)
    updater.start()
    app.run(host="0.0.0.0", port=58784)
