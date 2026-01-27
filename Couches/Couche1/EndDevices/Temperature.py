from random import random


class Temperature:
    def __init__(self, sensor_id, location, ipv6_address="fe80::3"):
        self.sensor_id = sensor_id
        self.location = location
        self.ipv6_address = ipv6_address
        self.temperature = None

    def read_temperature(self):
        # Simulate reading temperature from a sensor
        self.temperature = round(random.uniform(-20.0, 40.0), 2)
        return self.temperature

    def get_sensor_info(self):
        return {
            "sensor_id": self.sensor_id,
            "location": self.location,
            "temperature": self.temperature
        }