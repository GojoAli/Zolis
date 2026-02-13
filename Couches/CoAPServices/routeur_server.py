import asyncio
import json
import os
import socket
import time

import aiocoap
import aiocoap.resource as resource

from Couches.CONF import CONF

COAP_LEADER_HOST = os.getenv("COAP_LEADER_HOST", "coap-leader")
LEADER_ADDR_FILE = os.getenv("LEADER_ADDR_FILE", "")
SHARED_KEY = os.getenv("SHARED_KEY", "zolis-key")
USE_THREAD_URI = os.getenv("USE_THREAD_URI", "1") == "1"
STRICT_THREAD = os.getenv("STRICT_THREAD", "0") == "1"
THREAD_TRY_TIMEOUT = float(os.getenv("THREAD_TRY_TIMEOUT", "1.0"))
IPV4_TRY_TIMEOUT = float(os.getenv("IPV4_TRY_TIMEOUT", "4.0"))
ROUTEUR_PUBLISH_MQTT = os.getenv("ROUTEUR_PUBLISH_MQTT", "0") == "1"


def mqtt_client():
    import paho.mqtt.client as mqtt

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"routeur-{int(time.time())}")
    host = os.getenv("MQTT_BROKER_ADDRESS", CONF.MQTT_BROKER_ADDRESS)
    port = int(os.getenv("MQTT_BROKER_PORT", str(CONF.MQTT_BROKER_PORT)))
    # Avoid hard failing at startup if DNS/broker is not ready yet.
    client.connect_async(host, port, 60)
    client.reconnect_delay_set(min_delay=1, max_delay=10)
    client.loop_start()
    return client


async def coap_post(protocol, uri, payload, timeout_s=3.0):
    request = aiocoap.Message(
        code=aiocoap.POST, uri=uri, payload=json.dumps(payload).encode("utf-8")
    )
    response = await asyncio.wait_for(protocol.request(request).response, timeout=timeout_s)
    data = response.payload.decode("utf-8", errors="replace")
    return json.loads(data)


def _resolve_ipv4(host):
    try:
        return socket.gethostbyname(host)
    except Exception:
        return host


def leader_uri():
    if USE_THREAD_URI and LEADER_ADDR_FILE:
        try:
            with open(LEADER_ADDR_FILE, "r", encoding="utf-8") as handle:
                addr = handle.read().strip()
            if addr:
                return f"coap://[{addr}]/collect"
        except Exception:
            pass
    if STRICT_THREAD:
        raise RuntimeError(f"thread address missing for leader: {LEADER_ADDR_FILE}")
    return None


async def collect_from_leader(protocol):
    errors = []
    candidates = []
    try:
        thread_uri = leader_uri()
        if thread_uri:
            candidates.append((thread_uri, THREAD_TRY_TIMEOUT))
    except Exception as exc:
        errors.append(f"thread-uri -> {type(exc).__name__}: {exc}")

    if not STRICT_THREAD:
        candidates.append((f"coap://{_resolve_ipv4(COAP_LEADER_HOST)}/collect", IPV4_TRY_TIMEOUT))

    for uri, timeout_s in candidates:
        try:
            return await coap_post(protocol, uri, {"key": SHARED_KEY}, timeout_s=timeout_s)
        except Exception as exc:
            errors.append(f"{uri} -> {type(exc).__name__}: {exc}")

    raise RuntimeError("leader unreachable; " + " | ".join(errors))


class CollectResource(resource.Resource):
    def __init__(self):
        super().__init__()
        self.client = mqtt_client() if ROUTEUR_PUBLISH_MQTT else None

    async def render_post(self, request):
        try:
            data = json.loads(request.payload.decode("utf-8", errors="replace"))
        except Exception:
            data = {}
        if data.get("key") != SHARED_KEY:
            return aiocoap.Message(code=aiocoap.UNAUTHORIZED, payload=b"invalid key")

        protocol = await aiocoap.Context.create_client_context()
        try:
            leader_payload = await collect_from_leader(protocol)
        except Exception as exc:
            payload = json.dumps({"error": str(exc)}).encode("utf-8")
            return aiocoap.Message(code=aiocoap.INTERNAL_SERVER_ERROR, payload=payload)
        finally:
            await protocol.shutdown()

        gps = leader_payload.get("gps", {})
        batt = leader_payload.get("battery", {})
        temp = leader_payload.get("temperature", {})

        payload = {
            "gps": {
                "latitude": gps.get("lat"),
                "longitude": gps.get("lon"),
            },
            "temperature": temp.get("temperature"),
            "humidite": temp.get("humidite"),
            "pression": temp.get("pression"),
            "batterie": batt.get("batterie"),
            "leader_id": leader_payload.get("leader_id"),
        }

        if self.client is not None:
            self.client.publish(CONF.MQTT_TOPIC, json.dumps(payload))

        return aiocoap.Message(payload=json.dumps(payload).encode("utf-8"))


def main():
    root = resource.Site()
    root.add_resource(["collect"], CollectResource())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(aiocoap.Context.create_server_context(root, bind=("0.0.0.0", 5683)))
    print("coap-routeur listening on 0.0.0.0:5683", flush=True)
    loop.run_forever()


if __name__ == "__main__":
    main()
