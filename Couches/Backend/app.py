import asyncio
import json
import os
import time
import math
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import aiocoap

from Couches.CONF import CONF
from Couches.Couche3.MQTT import MQTT
from Couches.Couche3.Validation import Validation
from Couches.Backend.db import SessionLocal, Runner, Session, Measure


COAP_GPS_HOST = os.getenv("COAP_GPS_HOST", "coap-gps")
COAP_BATTERY_HOST = os.getenv("COAP_BATTERY_HOST", "coap-batt")
COAP_TEMP_HOST = os.getenv("COAP_TEMP_HOST", "coap-temp")
POLL_INTERVAL = float(os.getenv("COAP_POLL_INTERVAL", "1.0"))
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
    """Distance en mètres entre deux points GPS (Haversine)."""
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


async def coap_get(protocol, uri):
    request = aiocoap.Message(code=aiocoap.GET, uri=uri)
    response = await protocol.request(request).response
    payload = response.payload.decode("utf-8", errors="replace")
    return json.loads(payload)


async def poll_loop():
    protocol = await aiocoap.Context.create_client_context()
    while True:
        try:
            gps = await coap_get(protocol, f"coap://{COAP_GPS_HOST}/gps")
            batt = await coap_get(protocol, f"coap://{COAP_BATTERY_HOST}/battery")
            temp = await coap_get(protocol, f"coap://{COAP_TEMP_HOST}/temperature")

            if gps.get("key") != SHARED_KEY:
                await asyncio.sleep(POLL_INTERVAL)
                continue
            if batt.get("key") != SHARED_KEY:
                await asyncio.sleep(POLL_INTERVAL)
                continue
            if temp.get("key") != SHARED_KEY:
                await asyncio.sleep(POLL_INTERVAL)
                continue

            lat = gps.get("lat")
            lon = gps.get("lon")
            temperature = temp.get("temperature")
            humidite = temp.get("humidite")
            pression = temp.get("pression")
            batterie = batt.get("batterie")

            if not validator.check_gps(lat, lon):
                await asyncio.sleep(POLL_INTERVAL)
                continue
            if not validator.check_temp(temperature):
                await asyncio.sleep(POLL_INTERVAL)
                continue
            if not validator.check_humidite(humidite):
                await asyncio.sleep(POLL_INTERVAL)
                continue
            if not validator.check_pression(pression):
                await asyncio.sleep(POLL_INTERVAL)
                continue
            if batterie is None or not (0 <= batterie <= 100):
                await asyncio.sleep(POLL_INTERVAL)
                continue

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

            app.state.mqtt.publish(payload, topic=CONF.MQTT_TOPIC)
            _persist_measure(payload)
        except Exception:
            pass

        await asyncio.sleep(POLL_INTERVAL)


@app.on_event("startup")
async def startup():
    app.state.mqtt = MQTT(
        broker_host=CONF.MQTT_BROKER_ADDRESS,
        broker_port=CONF.MQTT_BROKER_PORT,
        client_id=CONF.MQTT_PRODUCER_ID,
        topic=CONF.MQTT_TOPIC,
    )
    app.state.last_point = None
    app.state.total_distance_m = 0.0
    app.state.current_session_id = None
    asyncio.create_task(poll_loop())


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
