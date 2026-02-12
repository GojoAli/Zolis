# On va créer un conteneur Docker pour exécuter le script Python de capteur de batterie
# Le conteneur sera basé sur une image Python officielle
FROM python:3.9-slim
# Définir le répertoire de travail dans le conteneur
WORKDIR /app
# Copier les fichiers nécessaires dans le conteneur
COPY . /app
# Installer les dépendances requises
RUN pip install --no-cache-dir -r requirements.txt
# Commande pour exécuter le script Python
CMD ["python3", "-m", "Couches.Main"]
