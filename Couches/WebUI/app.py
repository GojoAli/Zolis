import json
import os
import threading
import time
import urllib.error
import urllib.request

from flask import Flask, Response, jsonify, render_template, request
import paho.mqtt.client as mqtt

from Couches.CONF import CONF

BROKER_HOST = CONF.MQTT_BROKER_ADDRESS
BROKER_PORT = CONF.MQTT_BROKER_PORT
TOPIC = CONF.MQTT_TOPIC
CLIENT_ID = CONF.MQTT_CLIENT_ID

app = Flask(__name__)
BACKEND_HTTP = os.getenv("BACKEND_HTTP", "http://backend:8000")

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
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)
            client.on_message = on_message
            client.connect(BROKER_HOST, BROKER_PORT, 60)
            client.subscribe(TOPIC)
            client.loop_forever()
        except Exception:
            time.sleep(2)


@app.get("/")
def index():
    return render_template("index.html", backend_http=BACKEND_HTTP)


@app.get("/register")
def register():
    return render_template("register.html", backend_http=BACKEND_HTTP)


@app.get("/api/latest")
def api_latest():
    """Renvoie les dernières données reçues de MQTT."""
    with _lock:
        return jsonify(latest_data)


def _forward_backend(path, method="GET", payload=None, query_string=None):
    url = f"{BACKEND_HTTP}{path}"
    if query_string:
        url = f"{url}?{query_string.decode('utf-8')}"

    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read()
                content_type = resp.headers.get("Content-Type", "application/json")
                return Response(body, status=resp.status, content_type=content_type)
        except urllib.error.HTTPError as exc:
            return Response(exc.read(), status=exc.code, content_type="application/json")
        except Exception:
            time.sleep(0.4)

    return jsonify({"error": "backend unavailable"}), 502


@app.post("/api/backend/runners")
def api_backend_runners():
    return _forward_backend("/api/runners", method="POST", payload=request.get_json(silent=True) or {})


@app.post("/api/backend/collect")
def api_backend_collect():
    return _forward_backend("/api/collect", method="POST", payload={})


@app.get("/api/backend/sessions/<session_id>")
def api_backend_session(session_id):
    return _forward_backend(f"/api/sessions/{session_id}", method="GET")


@app.get("/api/backend/sessions/<session_id>/measures")
def api_backend_measures(session_id):
    return _forward_backend(
        f"/api/sessions/{session_id}/measures",
        method="GET",
        query_string=request.query_string,
    )


mqtt_thread = threading.Thread(target=mqtt_worker, daemon=True)
mqtt_thread.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
