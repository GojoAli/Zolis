class Routeur:
    """
    Le routeur est le capteur responsable de la reception des données du Leader.
    Il les enverra ensuite sur un Topic MQTT.
    """

    def __init__(self, ipv6_address="fe80::4"):
        self.ipv6_address = ipv6_address
    
    def send_data(self, data):
        """Simule l'envoi des données vers un Topic MQTT."""
        print(f"Envoi des données au Topic MQTT: {data}")