import random


class TemperatureSensor:
    def __init__(self, location, ipv6_address="fe80::3"):
        self.location = location
        self.ipv6_address = ipv6_address
        self.temp = None
        self.humidite = None
        self.pression = None

    def get_temp(self):
        """retourne une valeur de température simulée entre -40 et 60 degrés Celsius."""
        self.temp = round(random.uniform(-40.0, 60.0), 2)
        return self.temp

    def get_temperature(self):
        """Retourne les valeurs simulées de température, humidité et pression."""
        return (self.temp, self.humidite, self.pression)
    
    def get_humidite(self):
        """retourne une valeur d'humidité simulée entre 0 et 100%."""
        self.humidite = round(random.uniform(0.0, 100.0), 2)
        return self.humidite
    
    def get_pression(self):
        """retourne une valeur de pression atmosphérique simulée entre 900 et 1100 hPa."""
        self.pression = round(random.uniform(900.0, 1100.0), 2)
        return self.pression


    def get_location(self):
        """Retourne la localisation associée au capteur de température."""
        return self.location
    
    def get_ipv6_address(self):
        """Retourne l'adresse IPv6 du capteur de température."""
        return self.ipv6_address
    
    def simulate_temperature_change(self):
        """Simule un changement de température en modifiant légèrement la valeur actuelle."""

        self.temp = self.get_temp() + random.uniform(-0.5, 0.5)
        self.humidite = self.get_humidite() + random.uniform(-1.0, 1.0)
        self.pression = self.get_pression() + random.uniform(-0.5, 0.5)
