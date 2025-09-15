from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'auth_user'
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return f"{self.email}"

    @property
    def full_name(self):
        """Retourne le nom complet de l'utilisateur"""
        return f"{self.username}".strip()

    def get_short_name(self):
        """Retourne le prénom de l'utilisateur"""
        return self.username
    
