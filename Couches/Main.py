import os
import time

from Couches.Couche1.EndDevices.Batterie import BatterieSensor
from Couches.Couche1.EndDevices.GPS import GPSSensor
from Couches.Couche1.EndDevices.Temperature import TemperatureSensor
from Couches.Couche1.Leader import Leader
from Couches.Couche1.Routeur import Routeur
from Couches.Couche3.MQTT import MQTT
from Couches.CONF import CONF




def main():
    mqtt_client = MQTT(broker_host=CONF.MQTT_BROKER_ADDRESS, broker_port=CONF.MQTT_BROKER_PORT, client_id=CONF.MQTT_PRODUCER_ID, topic=CONF.MQTT_TOPIC)

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
        routeur.send_data(routeur.data, mqtt_client, topic=CONF.MQTT_TOPIC)

        time.sleep(1)


if __name__ == "__main__":
    main()
