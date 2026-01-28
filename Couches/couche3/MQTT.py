import json
from time import sleep
import paho.mqtt.client as mqtt

from Couches.CONF import CONF

class MQTT:
    """
    La classe MQTT est responsable de la gestion de la communication MQTT.
    Elle envoie les données reçues du Routeur vers un broker MQTT.
    """

    def __init__(self, broker_host=CONF.MQTT_BROKER_ADDRESS, broker_port=CONF.MQTT_BROKER_PORT, client_id=CONF.MQTT_CLIENT_ID, topic=CONF.MQTT_TOPIC):
        self.broker_host = broker_host
        self.broker_port = broker_port

        self.topic = topic

        self.client = mqtt.Client(client_id=client_id)

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message


        self.client.connect(self.broker_host, self.broker_port, 60)

        self.client.loop_start()
    
    def on_connect(self, client, userdata, flags, rc):
        self.client.subscribe(self.topic)

    
    def on_disconnect(self, client, userdata, rc):
        print("MQTT déconnecté")
    

    def publish(self, data):
        """Publication des données sur un topic MQTT."""
        data= json.dumps(data)
        result = self.client.publish(self.topic, str(data))
        
    
    def subscribe(self):
        """Simule l'abonnement à un topic MQTT."""
        self.client.subscribe(self.topic)
        print(f"Abonné au topic {self.topic}")

    def on_message(self, client, userdata, msg):
        print(f"Message reçu {msg.payload.decode()}")





if __name__ == "__main__":
    mqtt_client = MQTT(broker_host="localhost", broker_port=1883, client_id="TestClient", topic="test/topic")
    sleep(1)  # laisse le temps de s'abonner
    mqtt_client.subscribe()
    mqtt_client.publish({"message": "Helklo, MQTT!"})
    sleep(5)
