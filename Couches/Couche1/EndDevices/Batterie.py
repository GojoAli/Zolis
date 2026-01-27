class Batterie:
    def __init__(self, niveau_initial=100, ipv6_address="fe80::1"):
        self.niveau = niveau_initial  # Niveau de batterie en pourcentage
        self.ipv6_address = ipv6_address

    def consommer(self, quantite):
        """Consomme une certaine quantité de batterie."""
        if quantite < 0:
            raise ValueError("La quantité à consommer doit être positive.")
        self.niveau = max(0, self.niveau - quantite)

    def recharger(self, quantite):
        """Recharge la batterie d'une certaine quantité."""
        if quantite < 0:
            raise ValueError("La quantité à recharger doit être positive.")
        self.niveau = min(100, self.niveau + quantite)

    def get_niveau(self):
        """Retourne le niveau actuel de la batterie."""
        return self.niveau
    
    def simulate_drain(self, taux_drain):
        """Simule la décharge de la batterie sur une période donnée."""
        if taux_drain < 0:
            raise ValueError("Le taux de décharge doit être positif.")
        self.niveau = max(0, self.niveau - taux_drain)