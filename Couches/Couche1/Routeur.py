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
        mqtt.publish(data)
        print(f"Envoi des données au broker MQTT sur le topic {publish_topic}: {data}")

