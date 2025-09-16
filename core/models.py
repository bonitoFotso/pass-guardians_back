"""
Modèles et classes de base partagés
"""
from django.db import models
import uuid


class BaseModel(models.Model):
    """Modèle de base avec UUID et timestamps"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class PermissionChoices(models.TextChoices):
    """Choix de permissions pour le partage"""
    READ = 'read', 'Lecture'
    WRITE = 'write', 'Écriture' 
    SHARE = 'share', 'Partage'
    ADMIN = 'admin', 'Administration'