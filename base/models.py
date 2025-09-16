from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid
from django.contrib.auth import get_user_model
User = get_user_model()


class AppSettings(models.Model):
    """Paramètres d'application par utilisateur"""
    
    class ThemeChoices(models.TextChoices):
        LIGHT = 'light', 'Clair'
        DARK = 'dark', 'Sombre'
        SYSTEM = 'system', 'Système'
    
    class TimeoutChoices(models.IntegerChoices):
        NEVER = 0, 'Jamais'
        FIVE_MIN = 300, '5 minutes'
        TEN_MIN = 600, '10 minutes'
        THIRTY_MIN = 1800, '30 minutes'
        ONE_HOUR = 3600, '1 heure'
        TWO_HOURS = 7200, '2 heures'
    
    class ClipboardTimeoutChoices(models.IntegerChoices):
        TEN_SEC = 10, '10 secondes'
        THIRTY_SEC = 30, '30 secondes'
        ONE_MIN = 60, '1 minute'
        FIVE_MIN = 300, '5 minutes'
        NEVER = 0, 'Jamais'
    
    class ExportFormatChoices(models.TextChoices):
        CSV = 'csv', 'CSV'
        JSON = 'json', 'JSON'
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='app_settings')
    
    # Apparence
    theme = models.CharField(max_length=10, choices=ThemeChoices.choices, default=ThemeChoices.SYSTEM)
    
    # Sécurité
    auto_lock_timeout = models.PositiveIntegerField(choices=TimeoutChoices.choices, default=TimeoutChoices.THIRTY_MIN)
    clipboard_clear_timeout = models.PositiveIntegerField(choices=ClipboardTimeoutChoices.choices, default=ClipboardTimeoutChoices.THIRTY_SEC)
    enable_biometric = models.BooleanField(default=False)
    
    # Interface
    show_password_strength = models.BooleanField(default=True)
    auto_fill_enabled = models.BooleanField(default=True)
    
    # Notifications
    breach_monitoring = models.BooleanField(default=True)
    login_notifications = models.BooleanField(default=True)
    
    # Export
    export_format = models.CharField(max_length=10, choices=ExportFormatChoices.choices, default=ExportFormatChoices.CSV)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Paramètres Application'
        verbose_name_plural = 'Paramètres Applications'
    
    def __str__(self):
        return f"Paramètres de {self.user.email}"