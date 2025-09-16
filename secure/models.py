# models/security.py
"""
Modèles pour la sécurité, l'audit et les alertes
"""
from django.db import models

from core.models import BaseModel
from django.contrib.auth import get_user_model
User = get_user_model()


class SecurityLog(BaseModel):
    """Logs de sécurité pour l'audit"""
    
    class ActionChoices(models.TextChoices):
        # Actions utilisateur
        USER_LOGIN = 'user_login', 'Connexion utilisateur'
        USER_LOGOUT = 'user_logout', 'Déconnexion utilisateur'
        USER_LOGIN_FAILED = 'user_login_failed', 'Échec de connexion'
        USER_PASSWORD_CHANGED = 'user_password_changed', 'Mot de passe changé'
        USER_2FA_ENABLED = 'user_2fa_enabled', '2FA activé'
        USER_2FA_DISABLED = 'user_2fa_disabled', '2FA désactivé'
        
        # Actions sur les credentials
        CREDENTIAL_CREATED = 'credential_created', 'Credential créé'
        CREDENTIAL_UPDATED = 'credential_updated', 'Credential modifié'
        CREDENTIAL_DELETED = 'credential_deleted', 'Credential supprimé'
        CREDENTIAL_VIEWED = 'credential_viewed', 'Credential consulté'
        CREDENTIAL_PASSWORD_REVEALED = 'credential_password_revealed', 'Mot de passe révélé'
        CREDENTIAL_SHARED = 'credential_shared', 'Credential partagé'
        CREDENTIAL_UNSHARED = 'credential_unshared', 'Partage retiré'
        
        # Actions sur les dossiers
        FOLDER_CREATED = 'folder_created', 'Dossier créé'
        FOLDER_UPDATED = 'folder_updated', 'Dossier modifié'
        FOLDER_DELETED = 'folder_deleted', 'Dossier supprimé'
        FOLDER_SHARED = 'folder_shared', 'Dossier partagé'
        
        # Actions de sécurité
        SUSPICIOUS_ACTIVITY = 'suspicious_activity', 'Activité suspecte'
        DATA_EXPORT = 'data_export', 'Export de données'
        DATA_IMPORT = 'data_import', 'Import de données'
    
    class ResourceTypeChoices(models.TextChoices):
        USER = 'user', 'Utilisateur'
        CREDENTIAL = 'credential', 'Credential'
        FOLDER = 'folder', 'Dossier'
        SYSTEM = 'system', 'Système'
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='security_logs')
    action = models.CharField(max_length=50, choices=ActionChoices.choices, db_index=True)
    resource_id = models.UUIDField(null=True, blank=True)
    resource_type = models.CharField(max_length=20, choices=ResourceTypeChoices.choices, default=ResourceTypeChoices.SYSTEM)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField()
    location = models.CharField(max_length=100, blank=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    is_suspicious = models.BooleanField(default=False, db_index=True)
    
    class Meta:
        verbose_name = 'Log de Sécurité'
        verbose_name_plural = 'Logs de Sécurité'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['is_suspicious', 'timestamp']),
        ]
    
    def __str__(self):
        user_info = f" par {self.user.email}" if self.user else ""
        return f"{self.get_action_display()}{user_info} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

