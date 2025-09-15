#!/bin/bash

echo "🚀 Démarrage de l'application Django..."

# Attendre que la base de données soit disponible
echo "⏳ Attente de la base de données..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "✅ Base de données disponible"

# Appliquer les migrations
echo "📦 Application des migrations..."
python manage.py makemigrations
python manage.py migrate

# Collecter les fichiers statiques
echo "📁 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# Créer un superutilisateur si il n'existe pas
echo "👤 Création du superutilisateur..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123',
        first_name='Admin',
        last_name='User'
    )
    print('Superutilisateur créé: admin@example.com / admin123')
else:
    print('Superutilisateur déjà existant')
"

# Démarrer le serveur de développement
echo "🎯 Démarrage du serveur Django..."
if [ "$DEBUG" = "True" ]; then
    echo "Mode développement activé"
    python manage.py runserver 0.0.0.0:8000
else
    echo "Mode production activé"
    gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
fi