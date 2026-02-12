import asyncio
import json
import time
import os

import aiocoap
import aiocoap.resource as resource

from Couches.Couche1.EndDevices.Temperature import TemperatureSensor


class TemperatureResource(resource.Resource):
    def __init__(self):
        super().__init__()
        self.sensor = TemperatureSensor(location="Paris")
        self.key = os.getenv("SHARED_KEY", "zolis-key")

    async def render_get(self, request):
        self.sensor.simulate_temperature_change()
        payload = {
            "temperature": self.sensor.temp,
            "humidite": self.sensor.humidite,
            "pression": self.sensor.pression,
            "timestamp": time.time(),
            "key": self.key,
        }
        return aiocoap.Message(payload=json.dumps(payload).encode("utf-8"))


def main():
    root = resource.Site()
    root.add_resource(["temperature"], TemperatureResource())
    asyncio.get_event_loop().create_task(aiocoap.Context.create_server_context(root))
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
