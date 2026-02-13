import asyncio
import hashlib
import hmac
import ipaddress
import json
import math
import os
import secrets
import socket
import time
import uuid

import aiocoap
import paho.mqtt.client as mqtt
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from Couches.Backend.db import Measure, Runner, RunnerCredential, RunnerDevice, Session, SessionLocal
from Couches.CONF import CONF
from Couches.Couche3.Validation import Validation

COAP_ROUTEUR_HOST = os.getenv("COAP_ROUTEUR_HOST", "coap-routeur")
SHARED_KEY = os.getenv("SHARED_KEY", "zolis-key")
COLLECT_RETRIES = int(os.getenv("COLLECT_RETRIES", "1"))
COLLECT_DELAY_S = float(os.getenv("COLLECT_DELAY_S", "0.3"))
COLLECT_TIMEOUT_S = float(os.getenv("COLLECT_TIMEOUT_S", "8.0"))
PASSWORD_MIN_LEN = int(os.getenv("PASSWORD_MIN_LEN", "8"))

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


def _normalize_email(email):
    return (email or "").strip().lower()


def _hash_password(password):
    salt = secrets.token_hex(16)
    iterations = 200000
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def _verify_password(password, encoded):
    try:
        algo, iterations, salt, expected = encoded.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


def _normalize_devices(devices):
    if not isinstance(devices, dict):
        raise HTTPException(status_code=400, detail="devices is required")

    gps = (devices.get("gps") or "").strip()
    batterie = (devices.get("batterie") or "").strip()
    temperature = (devices.get("temperature") or "").strip()

    if not gps or not batterie or not temperature:
        raise HTTPException(status_code=400, detail="gps, batterie and temperature IPv6 are required")

    for label, value in {
        "gps": gps,
        "batterie": batterie,
        "temperature": temperature,
    }.items():
        try:
            addr = ipaddress.ip_address(value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"{label} is not a valid IP address")
        if addr.version != 6:
            raise HTTPException(status_code=400, detail=f"{label} must be IPv6")

    return {"gps": gps, "batterie": batterie, "temperature": temperature}


def _device_payload(db, runner_id):
    device = db.get(RunnerDevice, runner_id)
    if device is None:
        return None
    return {
        "gps": device.gps_ipv6,
        "batterie": device.batterie_ipv6,
        "temperature": device.temperature_ipv6,
    }


def _set_runner_devices(db, runner_id, devices):
    existing = db.get(RunnerDevice, runner_id)
    if existing is None:
        existing = RunnerDevice(
            runner_id=runner_id,
            gps_ipv6=devices["gps"],
            batterie_ipv6=devices["batterie"],
            temperature_ipv6=devices["temperature"],
        )
        db.add(existing)
    else:
        existing.gps_ipv6 = devices["gps"]
        existing.batterie_ipv6 = devices["batterie"]
        existing.temperature_ipv6 = devices["temperature"]


def _publish_session_topics(session_id, payload):
    client = getattr(app.state, "mqtt_sub", None)
    if client is None:
        return

    now = time.time()
    gps_payload = {
        "session_id": session_id,
        "lat": payload["gps"]["latitude"],
        "lon": payload["gps"]["longitude"],
        "timestamp": now,
    }
    temp_payload = {
        "session_id": session_id,
        "temperature": payload["temperature"],
        "humidite": payload["humidite"],
        "pression": payload["pression"],
        "timestamp": now,
    }
    batt_payload = {
        "session_id": session_id,
        "batterie": payload["batterie"],
        "timestamp": now,
    }
    latest_payload = dict(payload)
    latest_payload["ts"] = now

    client.publish(f"/tracking/{session_id}/gps", json.dumps(gps_payload))
    client.publish(f"/tracking/{session_id}/temperature", json.dumps(temp_payload))
    client.publish(f"/tracking/{session_id}/battery", json.dumps(batt_payload))
    client.publish(f"/tracking/{session_id}/latest", json.dumps(latest_payload))


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


def _extract_sensor_values(data):
    lat = data.get("gps", {}).get("latitude")
    lon = data.get("gps", {}).get("longitude")
    temperature = data.get("temperature")
    humidite = data.get("humidite")
    pression = data.get("pression")
    batterie = data.get("batterie")

    if not validator.check_gps(lat, lon):
        raise ValueError("invalid gps")
    if not validator.check_temp(temperature):
        raise ValueError("invalid temperature")
    if not validator.check_humidite(humidite):
        raise ValueError("invalid humidite")
    if not validator.check_pression(pression):
        raise ValueError("invalid pression")
    if batterie is None or not (0 <= batterie <= 100):
        raise ValueError("invalid batterie")

    return lat, lon, temperature, humidite, pression, batterie


async def coap_collect(retries=COLLECT_RETRIES, delay_s=COLLECT_DELAY_S):
    host = _resolve_ipv4(COAP_ROUTEUR_HOST)
    protocol = await aiocoap.Context.create_client_context()
    try:
        last_error = None
        for _ in range(retries):
            try:
                request = aiocoap.Message(
                    code=aiocoap.POST,
                    uri=f"coap://{host}/collect",
                    payload=json.dumps({"key": SHARED_KEY}).encode("utf-8"),
                )
                response = await asyncio.wait_for(
                    protocol.request(request).response, timeout=COLLECT_TIMEOUT_S
                )
                payload = response.payload.decode("utf-8", errors="replace")
                data = json.loads(payload)
                if isinstance(data, dict) and data.get("error"):
                    raise RuntimeError(data["error"])
                return data
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(delay_s)
        raise last_error if last_error else RuntimeError("collect failed")
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
    app.state.session_runtime = {}

    # Wait for PostgreSQL readiness before creating schema.
    from Couches.Backend.db import Base, engine

    last_error = None
    for _ in range(60):
        try:
            Base.metadata.create_all(bind=engine)
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(1)
    if last_error is not None:
        raise RuntimeError(f"database not ready after retry: {last_error}")


def on_mqtt_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        client.subscribe(CONF.MQTT_TOPIC)


@app.get("/api/latest")
def api_latest():
    return latest_data


def _find_runner_by_email(db, email):
    normalized = _normalize_email(email)
    return (
        db.query(Runner)
        .filter(Runner.email == normalized)
        .order_by(Runner.created_at.desc())
        .first()
    )


@app.post("/api/runners")
def create_runner(payload: dict):
    name = (payload.get("name") or "").strip()
    email = _normalize_email(payload.get("email"))
    password = payload.get("password") or ""
    devices = _normalize_devices(payload.get("devices"))
    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="name, email, password and devices are required")
    if len(password) < PASSWORD_MIN_LEN:
        raise HTTPException(
            status_code=400, detail=f"password must be at least {PASSWORD_MIN_LEN} chars"
        )

    with SessionLocal() as db:
        runner = _find_runner_by_email(db, email)
        if runner is not None:
            raise HTTPException(status_code=409, detail="email already registered")

        runner = Runner(id=str(uuid.uuid4()), name=name, email=email)
        db.add(runner)
        db.flush()
        credential = RunnerCredential(runner_id=runner.id, password_hash=_hash_password(password))
        db.add(credential)
        _set_runner_devices(db, runner.id, devices)

        run_session = Session(runner_id=runner.id)
        db.add(run_session)
        db.flush()
        db.commit()
        runner_id = runner.id
        runner_name = runner.name
        runner_email = runner.email
        run_session_id = run_session.id

    app.state.current_session_id = run_session_id

    runner_payload = {
        "id": runner_id,
        "name": runner_name,
        "email": runner_email,
        "devices": devices,
        "created_at": time.time(),
    }
    runners[runner_id] = runner_payload

    return {"runner": runner_payload, "session_id": run_session_id}


@app.post("/api/register")
def register(payload: dict):
    merged = dict(payload or {})
    merged.setdefault("devices", payload.get("devices") or {})
    return create_runner(merged)


@app.post("/api/login")
def login(payload: dict):
    email = _normalize_email(payload.get("email"))
    password = payload.get("password") or ""
    new_session = bool(payload.get("new_session", False))

    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    if not password:
        raise HTTPException(status_code=400, detail="password is required")

    with SessionLocal() as db:
        runner = _find_runner_by_email(db, email)
        if runner is None:
            raise HTTPException(status_code=404, detail="user not found")

        credential = db.get(RunnerCredential, runner.id)
        if credential is None or not _verify_password(password, credential.password_hash):
            raise HTTPException(status_code=401, detail="invalid credentials")

        run_session = None
        if not new_session:
            run_session = (
                db.query(Session)
                .filter(Session.runner_id == runner.id)
                .order_by(Session.started_at.desc())
                .first()
            )

        if run_session is None:
            run_session = Session(runner_id=runner.id)
            db.add(run_session)
            db.flush()

        db.commit()
        runner_payload = {
            "id": runner.id,
            "name": runner.name,
            "email": runner.email,
            "devices": _device_payload(db, runner.id),
        }
        run_session_id = run_session.id

    app.state.current_session_id = run_session_id

    return {
        "runner": runner_payload,
        "session_id": run_session_id,
    }


@app.get("/api/runners/{runner_id}/sessions")
def list_runner_sessions(runner_id: str, limit: int = 100):
    with SessionLocal() as db:
        runner = db.get(Runner, runner_id)
        if runner is None:
            raise HTTPException(status_code=404, detail="runner not found")

        sessions = (
            db.query(Session)
            .filter(Session.runner_id == runner_id)
            .order_by(Session.started_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": run_session.id,
                "runner_id": run_session.runner_id,
                "started_at": run_session.started_at.isoformat(),
                "total_distance_m": run_session.total_distance_m,
            }
            for run_session in sessions
        ]


@app.post("/api/runners/{runner_id}/sessions")
def create_runner_session(runner_id: str):
    with SessionLocal() as db:
        runner = db.get(Runner, runner_id)
        if runner is None:
            raise HTTPException(status_code=404, detail="runner not found")

        run_session = Session(runner_id=runner_id)
        db.add(run_session)
        db.flush()
        db.commit()
        run_session_id = run_session.id

    app.state.current_session_id = run_session_id
    return {"session_id": run_session_id}


def _runtime_for_session(db, session_id):
    runtime = app.state.session_runtime.get(session_id)
    if runtime is not None:
        return runtime

    last_measure = (
        db.query(Measure)
        .filter(Measure.session_id == session_id)
        .order_by(Measure.ts.desc())
        .first()
    )

    if last_measure is None:
        runtime = {"last_point": None, "total_distance_m": 0.0}
    else:
        runtime = {
            "last_point": (last_measure.lat, last_measure.lon),
            "total_distance_m": float(last_measure.distance_m),
        }

    app.state.session_runtime[session_id] = runtime
    return runtime


def _persist_measure(db, session_id, payload):
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

    run_session = db.get(Session, session_id)
    if run_session is not None:
        run_session.total_distance_m = payload["distance_m"]

    db.commit()


@app.post("/api/collect")
async def collect(payload: dict = Body(default_factory=dict)):
    try:
        raw = await coap_collect()
        if not isinstance(raw, dict):
            raise HTTPException(status_code=502, detail="invalid payload")

        session_id = (payload or {}).get("session_id") or app.state.current_session_id
        if not session_id:
            return raw

        with SessionLocal() as db:
            run_session = db.get(Session, session_id)
            if run_session is None:
                raise HTTPException(status_code=404, detail="session not found")

            lat, lon, temperature, humidite, pression, batterie = _extract_sensor_values(raw)

            runtime = _runtime_for_session(db, session_id)
            if runtime["last_point"] is not None:
                prev_lat, prev_lon = runtime["last_point"]
                runtime["total_distance_m"] += haversine_m(prev_lat, prev_lon, lat, lon)

            runtime["last_point"] = (lat, lon)
            distance_m = round(runtime["total_distance_m"], 2)

            processed = {
                "gps": {"latitude": lat, "longitude": lon},
                "temperature": temperature,
                "humidite": humidite,
                "pression": pression,
                "batterie": batterie,
                "distance_m": distance_m,
                "session_id": session_id,
            }

            _persist_measure(db, session_id, processed)

        _publish_session_topics(session_id, processed)
        latest_data.update(processed)
        latest_data["ts"] = time.time()
        return processed
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"collect unavailable: {type(exc).__name__}: {exc}"
        )


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    with SessionLocal() as db:
        run_session = db.get(Session, session_id)
        if run_session is None:
            raise HTTPException(status_code=404, detail="session not found")
        return {
            "id": run_session.id,
            "runner_id": run_session.runner_id,
            "started_at": run_session.started_at.isoformat(),
            "total_distance_m": run_session.total_distance_m,
        }


@app.get("/api/sessions/{session_id}/measures")
def get_measures(session_id: str, limit: int = 1000):
    with SessionLocal() as db:
        run_session = db.get(Session, session_id)
        if run_session is None:
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


@app.get("/api/sessions/{session_id}/latest")
def get_session_latest(session_id: str):
    with SessionLocal() as db:
        run_session = db.get(Session, session_id)
        if run_session is None:
            raise HTTPException(status_code=404, detail="session not found")

        measure = (
            db.query(Measure)
            .filter(Measure.session_id == session_id)
            .order_by(Measure.ts.desc())
            .first()
        )

        if measure is None:
            return {
                "gps": {"latitude": 0.0, "longitude": 0.0},
                "temperature": None,
                "humidite": None,
                "pression": None,
                "batterie": None,
                "distance_m": 0.0,
                "session_id": session_id,
                "ts": None,
            }

        return {
            "gps": {"latitude": measure.lat, "longitude": measure.lon},
            "temperature": measure.temperature,
            "humidite": measure.humidite,
            "pression": measure.pression,
            "batterie": measure.batterie,
            "distance_m": measure.distance_m,
            "session_id": session_id,
            "ts": measure.ts.timestamp(),
        }


def on_mqtt_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8", errors="replace"))
    except Exception:
        return

    try:
        lat, lon, temperature, humidite, pression, batterie = _extract_sensor_values(data)
    except Exception:
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
