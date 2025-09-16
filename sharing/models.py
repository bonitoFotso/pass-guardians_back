# models/sharing.py
"""
Modèles pour le partage de credentials et dossiers
"""
from django.db import models
from django.utils import timezone

from core.models import BaseModel, PermissionChoices
from django.contrib.auth import get_user_model
User = get_user_model()



class SharedCredential(BaseModel):
    """Partage de credentials avec permissions granulaires"""
    credential = models.ForeignKey('Credential', on_delete=models.CASCADE, related_name='shared_with')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_credentials')
    permission = models.CharField(max_length=10, choices=PermissionChoices.choices, default=PermissionChoices.READ)
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credentials_shared')
    shared_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Credential Partagé'
        verbose_name_plural = 'Credentials Partagés'
        unique_together = [['credential', 'user']]
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['credential', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.credential.name} partagé avec {self.user.email}"
    
    @property
    def is_expired(self):
        """Vérifie si le partage a expiré"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def has_permission(self, permission: str) -> bool:
        """Vérifie si l'utilisateur a une permission spécifique"""
        permissions_hierarchy = {
            'read': 0,
            'write': 1, 
            'share': 2,
            'admin': 3
        }
        user_level = permissions_hierarchy.get(self.permission, 0)
        required_level = permissions_hierarchy.get(permission, 0)
        return user_level >= required_level and self.is_active and not self.is_expired


class SharedFolder(BaseModel):
    """Partage de dossiers avec permissions granulaires"""
    folder = models.ForeignKey('Folder', on_delete=models.CASCADE, related_name='shared_with')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_folders')
    permission = models.CharField(max_length=10, choices=PermissionChoices.choices, default=PermissionChoices.READ)
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders_shared')
    shared_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Dossier Partagé'
        verbose_name_plural = 'Dossiers Partagés'
        unique_together = [['folder', 'user']]
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['folder', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.folder.name} partagé avec {self.user.email}"
    
    @property
    def is_expired(self):
        """Vérifie si le partage a expiré"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def has_permission(self, permission: str) -> bool:
        """Vérifie si l'utilisateur a une permission spécifique"""
        permissions_hierarchy = {
            'read': 0,
            'write': 1,
            'share': 2, 
            'admin': 3
        }
        user_level = permissions_hierarchy.get(self.permission, 0)
        required_level = permissions_hierarchy.get(permission, 0)
        return user_level >= required_level and self.is_active and not self.is_expired