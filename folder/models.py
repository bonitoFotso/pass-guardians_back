# models/folder.py
"""
Modèles pour l'organisation en dossiers
"""
from django.db import models

from core.models import BaseModel
from django.contrib.auth import get_user_model
User = get_user_model()


class Folder(BaseModel):
    """Dossiers pour organiser les credentials"""
    
    class ColorChoices(models.TextChoices):
        RED = '#FF6B6B', 'Rouge'
        TURQUOISE = '#4ECDC4', 'Turquoise'
        BLUE = '#45B7D1', 'Bleu'
        GREEN = '#96CEB4', 'Vert'
        YELLOW = '#FFEAA7', 'Jaune'
        VIOLET = '#DDA0DD', 'Violet'
        ORANGE = '#FFB347', 'Orange'
        SKY_BLUE = '#87CEEB', 'Bleu ciel'
    
    name = models.CharField(max_length=100, db_index=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    color = models.CharField(max_length=7, choices=ColorChoices.choices, default=ColorChoices.BLUE)
    is_shared = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Dossier'
        verbose_name_plural = 'Dossiers'
        unique_together = [['name', 'parent', 'owner']]
        indexes = [
            models.Index(fields=['owner', 'name']),
            models.Index(fields=['parent']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.owner.email})"
    
    @property
    def full_path(self):
        """Retourne le chemin complet du dossier"""
        if self.parent:
            return f"{self.parent.full_path}/{self.name}"
        return self.name
    
    def get_descendants(self):
        """Retourne tous les dossiers descendants"""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
