import asyncio
import json
import time
import os

import aiocoap
import aiocoap.resource as resource

from Couches.Couche1.EndDevices.GPS import GPSSensor


class GPSResource(resource.Resource):
    def __init__(self):
        super().__init__()
        self.sensor = GPSSensor(latitude=48.8566, longitude=2.3522)
        self.key = os.getenv("SHARED_KEY", "zolis-key")

    async def render_get(self, request):
        self.sensor.simulate_movement(delta_latitude=0.0004, delta_longitude=0.0003)
        lat, lon = self.sensor.get_coordinates()
        payload = {
            "lat": lat,
            "lon": lon,
            "timestamp": time.time(),
            "key": self.key,
        }
        return aiocoap.Message(payload=json.dumps(payload).encode("utf-8"))


def main():
    root = resource.Site()
    root.add_resource(["gps"], GPSResource())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(aiocoap.Context.create_server_context(root, bind=("0.0.0.0", 5683)))
    print("coap-gps listening on 0.0.0.0:5683", flush=True)
    loop.run_forever()


if __name__ == "__main__":
    main()
