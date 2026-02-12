import asyncio
import json
import os
import random
import time

import aiocoap
import aiocoap.resource as resource


COAP_GPS_HOST = os.getenv("COAP_GPS_HOST", "coap-gps")
COAP_BATTERY_HOST = os.getenv("COAP_BATTERY_HOST", "coap-batt")
COAP_TEMP_HOST = os.getenv("COAP_TEMP_HOST", "coap-temp")
SHARED_KEY = os.getenv("SHARED_KEY", "zolis-key")
ELECTION_INTERVAL = float(os.getenv("ELECTION_INTERVAL", "20"))

CANDIDATES = ["gps", "temperature", "batterie"]


class LeaderState:
    def __init__(self):
        self.current_leader = random.choice(CANDIDATES)
        self.elected_at = time.time()

    def maybe_rotate(self):
        if time.time() - self.elected_at >= ELECTION_INTERVAL:
            self.current_leader = random.choice(CANDIDATES)
            self.elected_at = time.time()


async def coap_get(protocol, uri):
    request = aiocoap.Message(code=aiocoap.GET, uri=uri)
    response = await protocol.request(request).response
    payload = response.payload.decode("utf-8", errors="replace")
    return json.loads(payload)


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
        gps = await coap_get(protocol, f"coap://{COAP_GPS_HOST}/gps")
        batt = await coap_get(protocol, f"coap://{COAP_BATTERY_HOST}/battery")
        temp = await coap_get(protocol, f"coap://{COAP_TEMP_HOST}/temperature")

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
    asyncio.get_event_loop().create_task(aiocoap.Context.create_server_context(root))
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
