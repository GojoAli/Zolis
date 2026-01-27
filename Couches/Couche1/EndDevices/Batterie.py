class BatterieSensor:
    def __init__(self, niveau_initial=100, ipv6_address="fe80::1"):
        """Initialise la batterie avec un niveau initial (par défaut à 100%)."""

        self.niveau = niveau_initial  
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
    
    def get_ipv6_address(self):
        """Retourne l'adresse IPv6 de la batterie."""
        return self.ipv6_address
    
    def simulate_drain(self, taux_drain):
        """Simule la décharge de la batterie sur une période donnée."""
        if taux_drain < 0:
            raise ValueError("Le taux de décharge doit être positif.")
        self.niveau = max(0, self.niveau - taux_drain)