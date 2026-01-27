from time import sleep
from EndDevices.GPS import GPSSensor

from EndDevices.Batterie import BatterieSensor

from EndDevices.Temperature import TemperatureSensor

from Leader import Leader
from Routeur import Routeur


batterie = BatterieSensor()
gps = GPSSensor()
temperature = TemperatureSensor(location="Paris")  

leader = Leader()
router = Routeur()


while batterie.get_niveau() > 0:
    # Simuler des changements

    print("----- Nouvelle itération -----")
    gps.simulate_movement(0.0001, 0.0001)
    temperature.simulate_temperature_change()
    batterie.simulate_drain(1) 


    leader.format_data(gps, temperature, batterie)
    leader.send_data(router)


    router.get_leader_data(leader)
    

    print("routeur data:", router.data)

    sleep(1)  # Pause d'une seconde entre les itérations