class Validation:
    """Classe Validation qui vérifie l'intégrité des données reçues."""
    def __init__(self):
        pass

    def check_temp(self, temperature):
        """Valide que la température est dans une plage acceptable."""
        return -40 <= temperature <= 60

    def check_humidite(self, humidite):
        """Valide que l'humidité est dans une plage acceptable."""
        return 0 <= humidite <= 100

    def check_pression(self, pression):
        """Valide que la pression est dans une plage acceptable."""
        return 900 <= pression <= 1100
    
    def check_gps(self, latitude, longitude):
        """Valide que les coordonnées GPS sont dans des plages acceptables."""
        return -90 <= latitude <= 90 and -180 <= longitude <= 180
    
