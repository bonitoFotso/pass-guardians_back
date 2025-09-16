# models/credential.py
"""
Modèles pour les credentials et leur gestion
"""
from django.db import models
from django.utils import timezone
from django.conf import settings
from cryptography.fernet import Fernet

from core.models import BaseModel
from django.contrib.auth import get_user_model
User = get_user_model()

class Category(BaseModel):
    """Catégories pour organiser les credentials"""
    
    class CategoryIcons(models.TextChoices):
        WEB = 'web', 'Site Web'
        EMAIL = 'email', 'Email'
        SOCIAL = 'social', 'Réseau Social'
        BANK = 'bank', 'Banque'
        WORK = 'work', 'Travail'
        PERSONAL = 'personal', 'Personnel'
        SHOPPING = 'shopping', 'Shopping'
        ENTERTAINMENT = 'entertainment', 'Divertissement'
        UTILITIES = 'utilities', 'Utilitaires'
        OTHER = 'other', 'Autre'
    
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=20, choices=CategoryIcons.choices, default=CategoryIcons.OTHER)
    color = models.CharField(max_length=7, default='#6C757D')
    is_system = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Credential(BaseModel):
    """Credential avec chiffrement sécurisé"""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credentials')
    name = models.CharField(max_length=255, db_index=True)
    username = models.CharField(max_length=255, blank=True)
    password_encrypted = models.BinaryField()
    url = models.URLField(blank=True)
    notes_encrypted = models.BinaryField(blank=True)
    
    # Relations
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    folder = models.ForeignKey('Folder', on_delete=models.CASCADE, null=True, blank=True, related_name='credentials')
    
    # Métadonnées
    is_favorite = models.BooleanField(default=False, db_index=True)
    is_shared = models.BooleanField(default=False, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    password_strength = models.PositiveSmallIntegerField(default=0)  # 0-100
    password_changed_at = models.DateTimeField(auto_now_add=True)
    auto_generated = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Credential'
        verbose_name_plural = 'Credentials'
        indexes = [
            models.Index(fields=['owner', 'name']),
            models.Index(fields=['owner', 'is_favorite']),
            models.Index(fields=['owner', 'folder']),
            models.Index(fields=['created_at']),
            models.Index(fields=['last_used_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.owner.email})"
    
    def _get_fernet(self):
        """Retourne l'instance Fernet pour le chiffrement"""
        if not hasattr(settings, 'ENCRYPTION_KEY'):
            raise ValueError("ENCRYPTION_KEY non configurée dans les settings")
        return Fernet(settings.ENCRYPTION_KEY)
    
    def encrypt_password(self, password: str) -> None:
        """Chiffre et stocke le mot de passe"""
        if password:
            fernet = self._get_fernet()
            self.password_encrypted = fernet.encrypt(password.encode())
    
    def decrypt_password(self) -> str:
        """Déchiffre et retourne le mot de passe"""
        if self.password_encrypted:
            try:
                fernet = self._get_fernet()
                return fernet.decrypt(self.password_encrypted).decode()
            except Exception:
                return ""
        return ""
    
    def encrypt_notes(self, notes: str) -> None:
        """Chiffre et stocke les notes"""
        if notes:
            fernet = self._get_fernet()
            self.notes_encrypted = fernet.encrypt(notes.encode())
    
    def decrypt_notes(self) -> str:
        """Déchiffre et retourne les notes"""
        if self.notes_encrypted:
            try:
                fernet = self._get_fernet()
                return fernet.decrypt(self.notes_encrypted).decode()
            except Exception:
                return ""
        return ""
    
    def update_last_used(self):
        """Met à jour la date de dernière utilisation"""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])


class PasswordHistory(BaseModel):
    """Historique des mots de passe pour éviter la réutilisation"""
    credential = models.ForeignKey(Credential, on_delete=models.CASCADE, related_name='password_history')
    password_hash = models.CharField(max_length=255)  # Hash du mot de passe
    
    class Meta:
        verbose_name = 'Historique Mot de Passe'
        verbose_name_plural = 'Historiques Mots de Passe'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['credential', 'created_at']),
        ]
    
    def __str__(self):
        return f"Historique de {self.credential.name} - {self.created_at.strftime('%Y-%m-%d')}"