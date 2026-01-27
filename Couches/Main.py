import os
import time

from Couche1.EndDevices.Batterie import BatterieSensor
from Couche1.EndDevices.GPS import GPSSensor
from Couche1.EndDevices.Temperature import TemperatureSensor
from Couche1.Leader import Leader
from Couche1.Routeur import Routeur
from couche3.MQTT import MQTT

BROKER_HOST = "localhost"
BROKER_PORT =1883
TOPIC = "Naruto Best Anime"


def main():
    mqtt_client = MQTT(broker_host=BROKER_HOST, broker_port=BROKER_PORT, client_id="Naruto", topic=TOPIC)

    gps = GPSSensor(latitude=48.8566, longitude=2.3522)
    temperature = TemperatureSensor(location="Paris")
    batterie = BatterieSensor(niveau_initial=100)

    leader = Leader()
    routeur = Routeur()

    while batterie.get_niveau() > 0:
        gps.simulate_movement(delta_latitude=0.0004, delta_longitude=0.0003)
        temperature.simulate_temperature_change()
        batterie.simulate_drain(taux_drain=0.5)

        leader.format_data(gps, temperature, batterie)
        leader.send_data(routeur)
        routeur.send_data(routeur.data, mqtt_client, topic=TOPIC)

        time.sleep(1)


if __name__ == "__main__":
    main()
