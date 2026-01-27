class GPS:
    def __init__(self, latitude=0.0, longitude=0.0, ipv6_address="fe80::2"):
        """Initialise le GPS avec des coordonnées par défaut (0.0, 0.0)."""
        self.latitude = latitude
        self.longitude = longitude
        self.ipv6_address = ipv6_address

    def set_coordinates(self, latitude, longitude):
        """Met à jour les coordonnées GPS."""
        self.latitude = latitude
        self.longitude = longitude

    def get_coordinates(self):
        """Retourne les coordonnées GPS actuelles sous forme de tuple (latitude, longitude)."""
        return self.latitude, self.longitude
    
    def simulate_movement(self, delta_latitude, delta_longitude):
        """Simule un déplacement en modifiant les coordonnées GPS."""
        self.latitude += delta_latitude
        self.longitude += delta_longitude