import os


class CONF:
    """Classe possédant les configurations globales de l'application."""
    MQTT_BROKER_ADDRESS = os.getenv("MQTT_BROKER_ADDRESS", "localhost")
    MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    MQTT_TOPIC = os.getenv("MQTT_TOPIC", "Naruto Best Anime")
    MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "NarutoClient")
    MQTT_PRODUCER_ID = os.getenv("MQTT_PRODUCER_ID", "NarutoProducer")
