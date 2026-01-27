class Auth:
    """Authentifier devices (clé partagée)"""
    
    def __init__(self, shared_key):
        self.shared_key = shared_key

    def authenticate(self, provided_key):
        """Vérifie si la clé fournie correspond à la clé partagée."""
        return self.shared_key == provided_key