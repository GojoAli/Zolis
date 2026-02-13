import json
import os
import threading
import time
import urllib.error
import urllib.request

from flask import Flask, Response, jsonify, redirect, render_template, request, session as flask_session, url_for
import paho.mqtt.client as mqtt

from Couches.CONF import CONF

BROKER_HOST = CONF.MQTT_BROKER_ADDRESS
BROKER_PORT = CONF.MQTT_BROKER_PORT
TOPIC = CONF.MQTT_TOPIC
CLIENT_ID = CONF.MQTT_CLIENT_ID
SUB_TOPIC = os.getenv("MQTT_SUB_TOPIC", "/tracking/#")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "zolis-dev-secret")
BACKEND_HTTP = os.getenv("BACKEND_HTTP", "http://backend:8000")
AUTH_SESSION_KEYS = ("session_id", "runner_id", "runner_name", "runner_email")

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
    with _lock:
        latest_data.clear()
        latest_data.update(data)
        latest_data["topic"] = TOPIC
        latest_data["ts"] = time.time()


def coerce_payload(payload):
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
    payload = msg.payload.decode("utf-8", errors="replace")
    data = coerce_payload(payload)
    if data is None:
        return

    if "gps" in data and isinstance(data["gps"], dict):
        set_latest(data)


def mqtt_worker():
    while True:
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)
            client.on_message = on_message
            client.connect(BROKER_HOST, BROKER_PORT, 60)
            client.subscribe(SUB_TOPIC)
            client.loop_forever()
        except Exception:
            time.sleep(2)


def _current_session_id():
    return flask_session.get("session_id")


def _current_runner_id():
    return flask_session.get("runner_id")


def _is_authenticated():
    return bool(_current_session_id() and _current_runner_id())


def _clear_auth_session():
    for key in AUTH_SESSION_KEYS:
        flask_session.pop(key, None)


def _backend_session_exists(session_id):
    if not session_id:
        return False
    url = f"{BACKEND_HTTP}/api/sessions/{session_id}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=3):
            return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        return True
    except Exception:
        # Do not force logout on transient backend/network issues.
        return True


@app.get("/")
def index():
    if not _is_authenticated():
        return redirect(url_for("login"))
    if not _backend_session_exists(_current_session_id()):
        _clear_auth_session()
        return redirect(url_for("login"))
    return render_template(
        "index.html",
        backend_http=BACKEND_HTTP,
        session_id=_current_session_id(),
        runner_name=flask_session.get("runner_name", "Utilisateur"),
    )


@app.get("/login")
def login():
    if _is_authenticated():
        return redirect(url_for("index"))
    return render_template("login.html")


@app.get("/register")
def register_page():
    if _is_authenticated():
        return redirect(url_for("index"))
    return render_template("register.html")


@app.get("/sessions")
def sessions_page():
    if not _is_authenticated():
        return redirect(url_for("login"))
    if not _backend_session_exists(_current_session_id()):
        _clear_auth_session()
        return redirect(url_for("login"))
    return render_template(
        "sessions.html",
        runner_name=flask_session.get("runner_name", "Utilisateur"),
        active_session_id=_current_session_id(),
    )


@app.get("/logout")
def logout():
    _clear_auth_session()
    return redirect(url_for("login"))


@app.post("/auth/session")
def set_auth_session():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    runner = data.get("runner") or {}
    if not session_id or not runner.get("id"):
        return jsonify({"error": "session_id and runner.id required"}), 400

    flask_session["session_id"] = session_id
    flask_session["runner_id"] = runner.get("id")
    flask_session["runner_name"] = runner.get("name") or "Utilisateur"
    flask_session["runner_email"] = runner.get("email")
    return jsonify({"ok": True})


@app.post("/auth/session/select")
def set_current_session():
    if not _is_authenticated():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    flask_session["session_id"] = session_id
    return jsonify({"ok": True})


@app.get("/api/latest")
def api_latest():
    with _lock:
        return jsonify(latest_data)


def _is_session_not_found_body(body_bytes):
    try:
        payload = json.loads(body_bytes.decode("utf-8", errors="replace") or "{}")
    except Exception:
        return False
    detail = (payload.get("detail") or payload.get("error") or "").lower()
    return "session not found" in detail


def _forward_backend(
    path,
    method="GET",
    payload=None,
    query_string=None,
    invalidate_session_on_404=False,
):
    url = f"{BACKEND_HTTP}{path}"
    if query_string:
        url = f"{url}?{query_string.decode('utf-8')}"

    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    timeout_s = 15 if path == "/api/collect" else 10
    attempts = 1 if path == "/api/collect" else 3
    last_error = "unknown error"

    for _ in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                body = resp.read()
                content_type = resp.headers.get("Content-Type", "application/json")
                return Response(body, status=resp.status, content_type=content_type)
        except urllib.error.HTTPError as exc:
            body = exc.read()
            if invalidate_session_on_404 and exc.code == 404 and _is_session_not_found_body(body):
                _clear_auth_session()
                return jsonify({"error": "session expired"}), 401
            return Response(body, status=exc.code, content_type="application/json")
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.4)

    return jsonify({"error": "backend unavailable", "detail": last_error}), 502


@app.post("/api/backend/login")
def api_backend_login():
    payload = request.get_json(silent=True) or {}
    return _forward_backend("/api/login", method="POST", payload=payload)


@app.post("/api/backend/register")
def api_backend_register():
    payload = request.get_json(silent=True) or {}
    return _forward_backend("/api/register", method="POST", payload=payload)


@app.post("/api/backend/runners")
def api_backend_runners():
    return _forward_backend("/api/runners", method="POST", payload=request.get_json(silent=True) or {})


@app.post("/api/backend/collect")
def api_backend_collect():
    payload = request.get_json(silent=True) or {}
    session_id = _current_session_id()
    if session_id:
        payload["session_id"] = session_id
    return _forward_backend(
        "/api/collect",
        method="POST",
        payload=payload,
        invalidate_session_on_404=True,
    )


@app.get("/api/backend/latest")
def api_backend_latest():
    session_id = _current_session_id()
    if session_id:
        return _forward_backend(
            f"/api/sessions/{session_id}/latest",
            method="GET",
            invalidate_session_on_404=True,
        )
    return _forward_backend("/api/latest", method="GET")


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


@app.get("/api/backend/my-sessions")
def api_backend_my_sessions():
    runner_id = _current_runner_id()
    if not runner_id:
        return jsonify({"error": "unauthorized"}), 401
    return _forward_backend(f"/api/runners/{runner_id}/sessions", method="GET")


@app.post("/api/backend/my-sessions")
def api_backend_create_session():
    runner_id = _current_runner_id()
    if not runner_id:
        return jsonify({"error": "unauthorized"}), 401
    return _forward_backend(f"/api/runners/{runner_id}/sessions", method="POST")


mqtt_thread = threading.Thread(target=mqtt_worker, daemon=True)
mqtt_thread.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
