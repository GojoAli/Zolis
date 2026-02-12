import asyncio
import json
import time
import os

import aiocoap
import aiocoap.resource as resource

from Couches.Couche1.EndDevices.Batterie import BatterieSensor


class BatteryResource(resource.Resource):
    def __init__(self):
        super().__init__()
        self.sensor = BatterieSensor(niveau_initial=100)
        self.key = os.getenv("SHARED_KEY", "zolis-key")

    async def render_get(self, request):
        self.sensor.simulate_drain(taux_drain=0.3)
        payload = {
            "batterie": self.sensor.get_niveau(),
            "timestamp": time.time(),
            "key": self.key,
        }
        return aiocoap.Message(payload=json.dumps(payload).encode("utf-8"))


def main():
    root = resource.Site()
    root.add_resource(["battery"], BatteryResource())
    asyncio.get_event_loop().create_task(aiocoap.Context.create_server_context(root))
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
