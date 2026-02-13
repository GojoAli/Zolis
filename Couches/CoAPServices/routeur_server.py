import asyncio
import json
import os
import socket
import time

import aiocoap
import aiocoap.resource as resource
import paho.mqtt.client as mqtt

from Couches.CONF import CONF

COAP_LEADER_HOST = os.getenv("COAP_LEADER_HOST", "coap-leader")
LEADER_ADDR_FILE = os.getenv("LEADER_ADDR_FILE", "")
SHARED_KEY = os.getenv("SHARED_KEY", "zolis-key")
USE_THREAD_URI = os.getenv("USE_THREAD_URI", "0") == "1"


def mqtt_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"routeur-{int(time.time())}")
    host = os.getenv("MQTT_BROKER_ADDRESS", CONF.MQTT_BROKER_ADDRESS)
    port = int(os.getenv("MQTT_BROKER_PORT", str(CONF.MQTT_BROKER_PORT)))
    # Avoid hard failing at startup if DNS/broker is not ready yet.
    client.connect_async(host, port, 60)
    client.reconnect_delay_set(min_delay=1, max_delay=10)
    client.loop_start()
    return client


async def coap_post(protocol, uri, payload):
    request = aiocoap.Message(
        code=aiocoap.POST, uri=uri, payload=json.dumps(payload).encode("utf-8")
    )
    response = await asyncio.wait_for(protocol.request(request).response, timeout=3)
    data = response.payload.decode("utf-8", errors="replace")
    return json.loads(data)


def _resolve_ipv4(host):
    try:
        return socket.gethostbyname(host)
    except Exception:
        return host


def leader_uri():
    if not USE_THREAD_URI:
        return None
    if LEADER_ADDR_FILE:
        try:
            with open(LEADER_ADDR_FILE, "r", encoding="utf-8") as handle:
                addr = handle.read().strip()
            if addr:
                return f"coap://[{addr}]/collect"
        except Exception:
            pass
    return None


async def collect_from_leader(protocol):
    errors = []
    candidates = []
    thread_uri = leader_uri()
    if thread_uri:
        candidates.append(thread_uri)
    candidates.append(f"coap://{_resolve_ipv4(COAP_LEADER_HOST)}/collect")

    for uri in candidates:
        try:
            return await coap_post(protocol, uri, {"key": SHARED_KEY})
        except Exception as exc:
            errors.append(f"{uri} -> {type(exc).__name__}: {exc}")

    raise RuntimeError("leader unreachable; " + " | ".join(errors))


class CollectResource(resource.Resource):
    def __init__(self):
        super().__init__()
        self.client = mqtt_client()

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
