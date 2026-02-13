import asyncio
import json
import math
import os
import socket
import time
import uuid

import aiocoap
import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from Couches.Backend.db import Measure, Runner, Session, SessionLocal
from Couches.CONF import CONF
from Couches.Couche3.Validation import Validation

COAP_ROUTEUR_HOST = os.getenv("COAP_ROUTEUR_HOST", "coap-routeur")
SHARED_KEY = os.getenv("SHARED_KEY", "zolis-key")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

latest_data = {
    "gps": {"latitude": 0.0, "longitude": 0.0},
    "temperature": None,
    "humidite": None,
    "pression": None,
    "batterie": None,
    "distance_m": 0.0,
    "topic": CONF.MQTT_TOPIC,
    "ts": None,
}

runners = {}
validator = Validation()


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _resolve_ipv4(host):
    try:
        return socket.gethostbyname(host)
    except Exception:
        return host


async def coap_collect():
    host = _resolve_ipv4(COAP_ROUTEUR_HOST)
    protocol = await aiocoap.Context.create_client_context()
    try:
        request = aiocoap.Message(
            code=aiocoap.POST,
            uri=f"coap://{host}/collect",
            payload=json.dumps({"key": SHARED_KEY}).encode("utf-8"),
        )
        response = await asyncio.wait_for(protocol.request(request).response, timeout=4)
        payload = response.payload.decode("utf-8", errors="replace")
        return json.loads(payload)
    finally:
        await protocol.shutdown()


@app.on_event("startup")
async def startup():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CONF.MQTT_CLIENT_ID)
    client.on_message = on_mqtt_message
    client.on_connect = on_mqtt_connect
    try:
        client.connect_async(CONF.MQTT_BROKER_ADDRESS, CONF.MQTT_BROKER_PORT, 60)
    except Exception:
        pass
    client.reconnect_delay_set(min_delay=1, max_delay=10)
    client.loop_start()
    app.state.mqtt_sub = client

    app.state.last_point = None
    app.state.total_distance_m = 0.0
    app.state.current_session_id = None

    # Keep backend usable without manual alembic command on a fresh volume.
    from Couches.Backend.db import Base, engine
    Base.metadata.create_all(bind=engine)


def on_mqtt_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        client.subscribe(CONF.MQTT_TOPIC)


@app.get("/api/latest")
def api_latest():
    return latest_data


@app.post("/api/runners")
def create_runner(payload: dict):
    name = payload.get("name")
    email = payload.get("email")
    devices = payload.get("devices", {})
    if not name or not email:
        raise HTTPException(status_code=400, detail="name and email are required")

    runner_id = str(uuid.uuid4())
    runners[runner_id] = {
        "id": runner_id,
        "name": name,
        "email": email,
        "devices": devices,
        "created_at": time.time(),
    }

    with SessionLocal() as db:
        runner = Runner(id=runner_id, name=name, email=email)
        db.add(runner)
        session = Session(runner_id=runner_id)
        db.add(session)
        db.commit()

        app.state.current_session_id = session.id

    return {"runner": runners[runner_id], "session_id": app.state.current_session_id}


@app.post("/api/collect")
async def collect():
    try:
        payload = await coap_collect()
        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"collect unavailable: {type(exc).__name__}: {exc}"
        )


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    with SessionLocal() as db:
        session = db.get(Session, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        return {
            "id": session.id,
            "runner_id": session.runner_id,
            "started_at": session.started_at.isoformat(),
            "total_distance_m": session.total_distance_m,
        }


@app.get("/api/sessions/{session_id}/measures")
def get_measures(session_id: str, limit: int = 1000):
    with SessionLocal() as db:
        session = db.get(Session, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        q = (
            db.query(Measure)
            .filter(Measure.session_id == session_id)
            .order_by(Measure.ts.asc())
            .limit(limit)
        )
        return [
            {
                "ts": m.ts.isoformat(),
                "lat": m.lat,
                "lon": m.lon,
                "temperature": m.temperature,
                "humidite": m.humidite,
                "pression": m.pression,
                "batterie": m.batterie,
                "distance_m": m.distance_m,
            }
            for m in q
        ]


def _persist_measure(payload):
    session_id = app.state.current_session_id
    if not session_id:
        return

    with SessionLocal() as db:
        measure = Measure(
            session_id=session_id,
            lat=payload["gps"]["latitude"],
            lon=payload["gps"]["longitude"],
            temperature=payload["temperature"],
            humidite=payload["humidite"],
            pression=payload["pression"],
            batterie=payload["batterie"],
            distance_m=payload["distance_m"],
        )
        db.add(measure)
        session = db.get(Session, session_id)
        if session is not None:
            session.total_distance_m = payload["distance_m"]
        db.commit()


def on_mqtt_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8", errors="replace"))
    except Exception:
        return

    lat = data.get("gps", {}).get("latitude")
    lon = data.get("gps", {}).get("longitude")
    temperature = data.get("temperature")
    humidite = data.get("humidite")
    pression = data.get("pression")
    batterie = data.get("batterie")

    if not validator.check_gps(lat, lon):
        return
    if not validator.check_temp(temperature):
        return
    if not validator.check_humidite(humidite):
        return
    if not validator.check_pression(pression):
        return
    if batterie is None or not (0 <= batterie <= 100):
        return

    if app.state.last_point is not None:
        prev_lat, prev_lon = app.state.last_point
        app.state.total_distance_m += haversine_m(prev_lat, prev_lon, lat, lon)
    app.state.last_point = (lat, lon)

    payload = {
        "gps": {"latitude": lat, "longitude": lon},
        "temperature": temperature,
        "humidite": humidite,
        "pression": pression,
        "batterie": batterie,
        "distance_m": round(app.state.total_distance_m, 2),
    }

    latest_data.update(payload)
    latest_data["ts"] = time.time()

    _persist_measure(payload)
