import mysql.connector
from mysql.connector import Error

class BDD:
    """Classe BDD qui gère la connexion et les opérations sur la base de données.
    C'est une base de données Mysql"""
    
    def __init__(self, db_name="zolis"):
        self.db_name = db_name
        self.db_user="root"
        self.db_password=""
        self.db_host="localhost"
        self.db_port=3306
        self.connection = None
    
    def connect(self):
        """Établit une connexion à la base de données."""
        try:
            self.connection = mysql.connector.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name
            )
            print("Connexion à la base de données réussie.")
        except mysql.connector.Error as err:
            print(f"Erreur de connexion à la base de données: {err}")
            self.connection = None

    def disconnect(self):
        """Ferme la connexion à la base de données."""
        if self.connection:
            self.connection.close()
            print("Connexion à la base de données fermée.")
    

    def insert_data(self, temperature, humidite, pression, latitude, longitude):
        """Insère des données dans la table 'data'."""
        if not self.connection:
            print("Pas de connexion à la base de données.")
            return
        
        try:
            cursor = self.connection.cursor()
            query = """
                INSERT INTO data (temperature, humidite, pression, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (temperature, humidite, pression, latitude, longitude))
            self.connection.commit()
            print("Données insérées avec succès.")
        except mysql.connector.Error as err:
            print(f"Erreur lors de l'insertion des données: {err}")
    

    def fetch_data(self):
        """Récupère toutes les données de la table 'data'."""
        if not self.connection:
            print("Pas de connexion à la base de données.")
            return []
        
        try:
            cursor = self.connection.cursor()
            query = "SELECT * FROM data"
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
        except mysql.connector.Error as err:
            print(f"Erreur lors de la récupération des données: {err}")
            return []
    
    def  delete_data(self, record_id):
        """Supprime une entrée de la table 'data' par son ID."""
        if not self.connection:
            print("Pas de connexion à la base de données.")
            return
        
        try:
            cursor = self.connection.cursor()
            query = "DELETE FROM data WHERE id = %s"
            cursor.execute(query, (record_id,))
            self.connection.commit()
            print(f"Donnée avec l'ID {record_id} supprimée avec succès.")
        except mysql.connector.Error as err:
            print(f"Erreur lors de la suppression des données: {err}")

    
    def update_data(self, record_id, temperature, humidite, pression, latitude, longitude):
        """Met à jour une entrée de la table 'data' par son ID."""
        if not self.connection:
            print("Pas de connexion à la base de données.")
            return
        
        try:
            cursor = self.connection.cursor()
            query = """
                UPDATE data
                SET temperature = %s, humidite = %s, pression = %s, latitude = %s, longitude = %s
                WHERE id = %s
            """
            cursor.execute(query, (temperature, humidite, pression, latitude, longitude, record_id))
            self.connection.commit()
            print(f"Donnée avec l'ID {record_id} mise à jour avec succès.")
        except mysql.connector.Error as err:
            print(f"Erreur lors de la mise à jour des données: {err}")

    def create_table_user(self, table_name="user_tab"):
        """Crée la table 'user' si elle n'existe pas déjà."""
        if not self.connection:
            print("Pas de connexion à la base de données.")
            return
        
        try:
            cursor = self.connection.cursor()
            query = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE,
                    password_hash VARCHAR(255)
                )
            """
            cursor.execute(query)
            self.connection.commit()
            print(f"Table '{table_name}' créée ou déjà existante.")
        except mysql.connector.Error as err:
            print(f"Erreur lors de la création de la table: {err}")

    def create_table_runing(self, table_name="runing_tab", table_user="user_tab"):
        """Crée la table 'runing' si elle n'existe pas déjà."""
        if not self.connection:
            print("Pas de connexion à la base de données.")
            return

        try:
            cursor = self.connection.cursor()
            query = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    temperature FLOAT,
                    humidite FLOAT,
                    pression FLOAT,
                    latitude FLOAT,
                    longitude FLOAT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    id_user INT ,
                    FOREIGN KEY (id_user) REFERENCES {table_user}(id)
                )
            """
            cursor.execute(query)
            self.connection.commit()
            print(f"Table '{table_name}' créée ou déjà existante.")
        except mysql.connector.Error as err:
            print(f"Erreur lors de la création de la table: {err}")

    def truncate_table(self, table_name):
        """Vide la table spécifiée."""
        if not self.connection:
            print("Pas de connexion à la base de données.")
            return
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            query = f"TRUNCATE TABLE {table_name}"
            cursor.execute(query)
            self.connection.commit()
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            print(f"Table '{table_name}' vidée avec succès.")
        except mysql.connector.Error as err:
            print(f"Erreur lors du vidage de la table: {err}")

    def insert_user(self, username, password_hash, table_name="user_tab"):
        """Insère un nouvel utilisateur dans la table 'user'."""
        if not self.connection:
            print("Pas de connexion à la base de données.")
            return
        
        try:
            cursor = self.connection.cursor()
            query = f"""
                INSERT INTO {table_name} (username, password_hash)
                VALUES (%s, %s)
            """
            cursor.execute(query, (username, password_hash))
            self.connection.commit()
            print("Utilisateur inséré avec succès.")
        except mysql.connector.Error as err:
            print(f"Erreur lors de l'insertion de l'utilisateur: {err}")


    def delete_user(self, user_id, table_name="user_tab"):
        """Supprime un utilisateur de la table 'user' par son ID."""
        if not self.connection:
            print("Pas de connexion à la base de données.")
            return
        
        try:
            cursor = self.connection.cursor()
            query = "DELETE FROM user WHERE id = %s"
            cursor.execute(query, (user_id,))
            self.connection.commit()
            print(f"Utilisateur avec l'ID {user_id} supprimé avec succès.")
        except mysql.connector.Error as err:
            print(f"Erreur lors de la suppression de l'utilisateur: {err}")


    def insert_runing(self, temperature, humidite, pression, latitude, longitude, id_user, table_name="runing"):
        """Insère des données dans la table 'runing'."""
        if not self.connection:
            print("Pas de connexion à la base de données.")
            return
        
        try:
            cursor = self.connection.cursor()
            query = f"""
                INSERT INTO {table_name} (temperature, humidite, pression, latitude, longitude, id_user)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (temperature, humidite, pression, latitude, longitude, id_user))
            self.connection.commit()
            print(f"Données insérées dans '{table_name}' avec succès.")
        except mysql.connector.Error as err:
            print(f"Erreur lors de l'insertion des données dans '{table_name}': {err}")

    
    def fetch_table(self, table_name="runing"):
        """Récupère toutes les données de la table '<table_name>'."""
        if not self.connection:
            print("Pas de connexion à la base de données.")
            return []

        try:
            cursor = self.connection.cursor()
            query = f"SELECT * FROM {table_name}"
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
        except mysql.connector.Error as err:
            print(f"Erreur lors de la récupération des données de '{table_name}': {err}")
            return []


    def delete_runing(self, record_id):
        """Supprime une entrée de la table 'runing' par son ID."""
        if not self.connection:
            print("Pas de connexion à la base de données.")
            return
        
        try:
            cursor = self.connection.cursor()
            query = "DELETE FROM runing WHERE id = %s"
            cursor.execute(query, (record_id,))
            self.connection.commit()
            print(f"Donnée dans 'runing' avec l'ID {record_id} supprimée avec succès.")
        except mysql.connector.Error as err:
            print(f"Erreur lors de la suppression des données de 'runing': {err}")
            

bdd = BDD()
bdd.connect()
bdd.create_table_user("user_tab")
bdd.create_table_runing("runing_tab", "user_tab")
bdd.insert_user("admin", "hashed_password", "user_tab")
bdd.insert_runing(25.5, 60.0, 1013.25, 48.8566, 2.3522, 1, "runing_tab")
print(bdd.fetch_table("user_tab"))
print(bdd.fetch_table("runing_tab"))
bdd.truncate_table("runing_tab")
bdd.truncate_table("user_tab")
bdd.disconnect()