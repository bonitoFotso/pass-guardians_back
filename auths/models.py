from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
class TimestampedModel(models.Model):
    """
    Modèle abstrait pour ajouter des champs de timestamp
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser, TimestampedModel):
    """
    Modèle utilisateur personnalisé qui étend AbstractUser
    Vous pouvez ajouter des champs supplémentaires selon vos besoins
    """
    email = models.EmailField(
        _('email address'),
        unique=True,
        help_text=_('Required. Enter a valid email address.')
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        help_text=_('Optional. Upload a profile picture.')
    )

    # Sécurité 2FA
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True)
    backup_codes = models.JSONField(default=list, blank=True)
    
    # Sécurité compte
    master_key_hash = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'auth_user'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.email}"

    @property
    def full_name(self):
        """Retourne le nom complet de l'utilisateur"""
        return f"{self.username}".strip()

    def get_short_name(self):
        """Retourne le prénom de l'utilisateur"""
        return self.username
    def save(self, *args, **kwargs):
        if self._state.adding:
            self.created_at = timezone.now()
        super().save(*args, **kwargs)
    
