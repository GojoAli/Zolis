import asyncio
import json
import os
import time

import aiocoap
import aiocoap.resource as resource
import paho.mqtt.client as mqtt

from Couches.CONF import CONF

COAP_LEADER_HOST = os.getenv("COAP_LEADER_HOST", "coap-leader")
SHARED_KEY = os.getenv("SHARED_KEY", "zolis-key")


def mqtt_client():
    client = mqtt.Client(client_id=f"routeur-{int(time.time())}")
    host = os.getenv("MQTT_BROKER_ADDRESS", CONF.MQTT_BROKER_ADDRESS)
    port = int(os.getenv("MQTT_BROKER_PORT", str(CONF.MQTT_BROKER_PORT)))
    client.connect(host, port, 60)
    return client


async def coap_post(protocol, uri, payload):
    request = aiocoap.Message(
        code=aiocoap.POST, uri=uri, payload=json.dumps(payload).encode("utf-8")
    )
    response = await protocol.request(request).response
    data = response.payload.decode("utf-8", errors="replace")
    return json.loads(data)


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
        leader_payload = await coap_post(
            protocol,
            f"coap://{COAP_LEADER_HOST}/collect",
            {"key": SHARED_KEY},
        )

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
    asyncio.get_event_loop().create_task(aiocoap.Context.create_server_context(root))
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
