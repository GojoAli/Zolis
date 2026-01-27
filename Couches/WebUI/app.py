import json
import os
import threading
import time

from flask import Flask, jsonify, render_template
import paho.mqtt.client as mqtt

BROKER_HOST = "localhost"
BROKER_PORT =1883
TOPIC = "Naruto Best Anime"
CLIENT_ID = "Sassuke"

app = Flask(__name__)

latest_data = {
    "gps": {"latitude": 0.0, "longitude": 0.0},
    "temperature": None,
    "humidite": None,
    "pression": None,
    "batterie": None,
    "topic": TOPIC,
    "ts": None,
}

_lock = threading.Lock()


def set_latest(data):
    """Met à jour les dernières données reçues de MQTT de manière thread-safe."""
    with _lock:
        latest_data.clear()
        latest_data.update(data)
        latest_data["topic"] = TOPIC
        latest_data["ts"] = time.time()

def coerce_payload(payload):
    """Tente de convertir la charge utile MQTT en dictionnaire."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return None

    if isinstance(data, dict):
        return data

    return None


def on_message(client, userdata, msg):
    """Gestionnaire d'événements pour les messages MQTT reçus."""
    payload = msg.payload.decode("utf-8", errors="replace")
    data = coerce_payload(payload)
    if data is None:
        return

    if "gps" in data and isinstance(data["gps"], dict):
        set_latest(data)


def mqtt_worker():
    """Thread worker pour gérer la connexion MQTT et recevoir les messages."""
    while True:
        try:
            client = mqtt.Client(client_id=CLIENT_ID)
            client.on_message = on_message
            client.connect(BROKER_HOST, BROKER_PORT, 60)
            client.subscribe(TOPIC)
            client.loop_forever()
        except Exception:
            time.sleep(2)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/latest")
def api_latest():
    """Renvoie les dernières données reçues de MQTT."""
    with _lock:
        return jsonify(latest_data)


mqtt_thread = threading.Thread(target=mqtt_worker, daemon=True)
mqtt_thread.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
