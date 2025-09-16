from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Créer un superutilisateur depuis les variables d\'environnement'

    def handle(self, *args, **options):
        username = os.environ.get('SUPERUSER_USERNAME')
        email = os.environ.get('SUPERUSER_EMAIL')
        password = os.environ.get('SUPERUSER_PASSWORD')

        # Vérifier que toutes les variables sont définies
        if not all([username, email, password]):
            self.stdout.write(
                self.style.ERROR(
                    'Veuillez définir SUPERUSER_USERNAME, SUPERUSER_EMAIL et SUPERUSER_PASSWORD dans votre fichier .env'
                )
            )
            return

        # Vérifier si l'utilisateur existe déjà
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'L\'utilisateur "{username}" existe déjà.')
            )
            return

        try:
            # Créer le superutilisateur
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Superutilisateur "{username}" créé avec succès !'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erreur lors de la création : {e}')
            )