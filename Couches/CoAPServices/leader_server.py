import asyncio
import json
import os
import random
import socket
import time

import aiocoap
import aiocoap.resource as resource


COAP_GPS_HOST = os.getenv("COAP_GPS_HOST", "coap-gps")
COAP_BATTERY_HOST = os.getenv("COAP_BATTERY_HOST", "coap-batt")
COAP_TEMP_HOST = os.getenv("COAP_TEMP_HOST", "coap-temp")
GPS_ADDR_FILE = os.getenv("GPS_ADDR_FILE", "")
BATTERY_ADDR_FILE = os.getenv("BATTERY_ADDR_FILE", "")
TEMP_ADDR_FILE = os.getenv("TEMP_ADDR_FILE", "")
SHARED_KEY = os.getenv("SHARED_KEY", "zolis-key")
ELECTION_INTERVAL = float(os.getenv("ELECTION_INTERVAL", "20"))
USE_THREAD_URI = os.getenv("USE_THREAD_URI", "1") == "1"
STRICT_THREAD = os.getenv("STRICT_THREAD", "0") == "1"
THREAD_TRY_TIMEOUT = float(os.getenv("THREAD_TRY_TIMEOUT", "1.0"))
IPV4_TRY_TIMEOUT = float(os.getenv("IPV4_TRY_TIMEOUT", "2.5"))

CANDIDATES = ["gps", "temperature", "batterie"]


class LeaderState:
    def __init__(self):
        self.current_leader = random.choice(CANDIDATES)
        self.elected_at = time.time()

    def maybe_rotate(self):
        if time.time() - self.elected_at >= ELECTION_INTERVAL:
            self.current_leader = random.choice(CANDIDATES)
            self.elected_at = time.time()


async def coap_get(protocol, uri, timeout_s=3.0):
    request = aiocoap.Message(code=aiocoap.GET, uri=uri)
    response = await asyncio.wait_for(protocol.request(request).response, timeout=timeout_s)
    payload = response.payload.decode("utf-8", errors="replace")
    return json.loads(payload)


def _resolve_ipv4(host):
    try:
        return socket.gethostbyname(host)
    except Exception:
        return host


def _addr_from_file(path):
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            addr = handle.read().strip()
        return addr or None
    except Exception:
        return None


def _coap_sensor_uris(addr_file, host, resource_name):
    thread_uri = None
    if USE_THREAD_URI:
        addr = _addr_from_file(addr_file)
        if addr:
            thread_uri = f"coap://[{addr}]/{resource_name}"
        elif STRICT_THREAD:
            raise RuntimeError(f"thread address missing for {resource_name}: {addr_file}")
    ipv4_uri = f"coap://{_resolve_ipv4(host)}/{resource_name}"
    return thread_uri, ipv4_uri


async def coap_get_with_fallback(protocol, addr_file, host, resource_name):
    errors = []
    thread_uri, ipv4_uri = _coap_sensor_uris(addr_file, host, resource_name)

    if thread_uri:
        try:
            return await coap_get(protocol, thread_uri, timeout_s=THREAD_TRY_TIMEOUT)
        except Exception as exc:
            errors.append(f"{thread_uri} -> {type(exc).__name__}: {exc}")
            if STRICT_THREAD:
                raise RuntimeError(
                    f"{resource_name} unreachable in strict thread mode; {' | '.join(errors)}"
                )

    try:
        return await coap_get(protocol, ipv4_uri, timeout_s=IPV4_TRY_TIMEOUT)
    except Exception as exc:
        errors.append(f"{ipv4_uri} -> {type(exc).__name__}: {exc}")
        raise RuntimeError(f"{resource_name} unreachable; {' | '.join(errors)}")


class CollectResource(resource.Resource):
    def __init__(self, state):
        super().__init__()
        self.state = state

    async def render_post(self, request):
        self.state.maybe_rotate()
        try:
            data = json.loads(request.payload.decode("utf-8", errors="replace"))
        except Exception:
            data = {}
        if data.get("key") != SHARED_KEY:
            return aiocoap.Message(code=aiocoap.UNAUTHORIZED, payload=b"invalid key")

        protocol = await aiocoap.Context.create_client_context()
        try:
            gps_task = coap_get_with_fallback(protocol, GPS_ADDR_FILE, COAP_GPS_HOST, "gps")
            batt_task = coap_get_with_fallback(
                protocol, BATTERY_ADDR_FILE, COAP_BATTERY_HOST, "battery"
            )
            temp_task = coap_get_with_fallback(protocol, TEMP_ADDR_FILE, COAP_TEMP_HOST, "temperature")
            gps, batt, temp = await asyncio.gather(gps_task, batt_task, temp_task)
        finally:
            await protocol.shutdown()

        payload = {
            "leader_id": self.state.current_leader,
            "leader_elected_at": self.state.elected_at,
            "gps": gps,
            "battery": batt,
            "temperature": temp,
        }
        return aiocoap.Message(payload=json.dumps(payload).encode("utf-8"))


def main():
    state = LeaderState()
    root = resource.Site()
    root.add_resource(["collect"], CollectResource(state))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(aiocoap.Context.create_server_context(root, bind=("0.0.0.0", 5683)))
    print("coap-leader listening on 0.0.0.0:5683", flush=True)
    loop.run_forever()


if __name__ == "__main__":
    main()
