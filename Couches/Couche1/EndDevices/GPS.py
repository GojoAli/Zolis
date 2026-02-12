import time


class GPSSensor:
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
    
    def get_ipv6_address(self):
        """Retourne l'adresse IPv6 du GPS."""
        return self.ipv6_address
    
    def simulate_movement(self, delta_latitude, delta_longitude):
        """Simule un déplacement en modifiant les coordonnées GPS."""
        self.latitude += delta_latitude
        self.longitude += delta_longitude


def main():
    sensor = GPSSensor(latitude=48.8566, longitude=2.3522)
    try:
        while True:
            sensor.simulate_movement(delta_latitude=0.0004, delta_longitude=0.0003)
            lat, lng = sensor.get_coordinates()
            print(f"GPS: {lat}, {lng}")
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
