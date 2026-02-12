class Leader:
    """
    Le leader est le capteur responsable de la reception des données du GPS, Température et Batterie.
    Il les enverra ensuite vers Le Routeur.
    Mais avant de les envoyer au routeur, il devra les mettre dans un format specifique.
    """
    
    def __init__(self, ipv6_address="fe80::4"):
        self.ipv6_address = ipv6_address


    def get_batterie_level(self, battery_sensor):
        """Récupère les données de la batterie."""
        return battery_sensor.get_niveau()

    def get_gps_coordinates(self, gps):
        """Récupère les coordonnées GPS."""
        return gps.get_coordinates()
    
    def get_temperature(self, temperature_sensor):
        """Récupère les données de température."""
        return temperature_sensor.get_temperature()

    def format_data(self, gps, temperature, battery):
        """Formate les données reçues en JSON."""
        data = {
            "gps": {
                "latitude": gps.get_coordinates()[0],
                "longitude": gps.get_coordinates()[1]
            },
            "temperature": temperature.get_temp(),
            "humidite": temperature.get_humidite(),
            "pression": temperature.get_pression(),
            "batterie": battery.get_niveau()
        }
        self.data = data
    

    
    def send_data(self, routeur):
        """Simule l'envoi des données formatées au Routeur."""
        routeur.set_leader_data(self)
        print(f"Envoi des données au Routeur à l'adresse {routeur.ipv6_address}: {self.data}")


def main():
    from Couches.Couche1.EndDevices.Batterie import BatterieSensor
    from Couches.Couche1.EndDevices.GPS import GPSSensor
    from Couches.Couche1.EndDevices.Temperature import TemperatureSensor
    import time

    gps = GPSSensor(latitude=48.8566, longitude=2.3522)
    temperature = TemperatureSensor(location="Paris")
    batterie = BatterieSensor(niveau_initial=100)

    leader = Leader()

    try:
        while True:
            gps.simulate_movement(delta_latitude=0.0004, delta_longitude=0.0003)
            temperature.simulate_temperature_change()
            batterie.simulate_drain(taux_drain=0.5)

            leader.format_data(gps, temperature, batterie)
            print(f"Leader data: {leader.data}")

            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
