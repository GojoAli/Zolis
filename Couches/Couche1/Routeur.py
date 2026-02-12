class Routeur:
    """
    Le routeur est le capteur responsable de la reception des données du Leader.
    Il les enverra ensuite sur un Topic MQTT.
    """

    def __init__(self, ipv6_address="fe80::5"):
        self.ipv6_address = ipv6_address
    
    def set_leader_data(self, leader):
        """Récupère les données envoyées par le Leader."""
        self.data=leader.data
        
        
    def send_data(self, data, mqtt, topic=None):
        """Simule l'envoi des données vers un Topic MQTT."""
        publish_topic = topic or self.ipv6_address
        mqtt.publish(data, topic=publish_topic)
        print(f"Envoi des données au broker MQTT sur le topic {publish_topic}: {data}")


def main():
    import time
    from Couches.Couche3.MQTT import MQTT
    from Couches.CONF import CONF

    mqtt_client = MQTT(
        broker_host=CONF.MQTT_BROKER_ADDRESS,
        broker_port=CONF.MQTT_BROKER_PORT,
        client_id=CONF.MQTT_CLIENT_ID,
        topic=CONF.MQTT_TOPIC,
    )

    routeur = Routeur()
    try:
        while True:
            if hasattr(routeur, "data"):
                routeur.send_data(routeur.data, mqtt_client, topic=CONF.MQTT_TOPIC)
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

