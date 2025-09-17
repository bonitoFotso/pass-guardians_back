# filters.py
"""
Filtres pour les modèles de partage
"""
import django_filters
from django.utils import timezone
from django.db.models import Q
from .models import SharedCredential, SharedFolder


class SharedCredentialFilter(django_filters.FilterSet):
    """
    Filtres pour les credentials partagés
    """
    # Filtres par statut
    is_active = django_filters.BooleanFilter(
        field_name='is_active',
        help_text='Filtrer par statut actif/inactif'
    )
    
    is_expired = django_filters.BooleanFilter(
        method='filter_by_expiration',
        help_text='Filtrer par expiration'
    )
    
    status = django_filters.ChoiceFilter(
        choices=[
            ('active', 'Actif'),
            ('inactive', 'Inactif'),
            ('expired', 'Expiré'),
        ],
        method='filter_by_status',
        help_text='Filtrer par statut global'
    )
    
    # Filtres par permission
    permission = django_filters.ChoiceFilter(
        choices=[
            ('read', 'Lecture'),
            ('write', 'Écriture'),
            ('share', 'Partage'),
            ('admin', 'Admin'),
        ],
        help_text='Filtrer par niveau de permission'
    )
    
    # Filtres par dates
    shared_after = django_filters.DateTimeFilter(
        field_name='shared_at',
        lookup_expr='gte',
        help_text='Partagé après cette date'
    )
    
    shared_before = django_filters.DateTimeFilter(
        field_name='shared_at',
        lookup_expr='lte',
        help_text='Partagé avant cette date'
    )
    
    expires_after = django_filters.DateTimeFilter(
        field_name='expires_at',
        lookup_expr='gte',
        help_text='Expire après cette date'
    )
    
    expires_before = django_filters.DateTimeFilter(
        field_name='expires_at',
        lookup_expr='lte',
        help_text='Expire avant cette date'
    )
    
    # Filtres par utilisateur
    user_email = django_filters.CharFilter(
        field_name='user__email',
        lookup_expr='icontains',
        help_text='Email de l\'utilisateur (contient)'
    )
    
    shared_by_email = django_filters.CharFilter(
        field_name='shared_by__email',
        lookup_expr='icontains',
        help_text='Email de celui qui partage (contient)'
    )
    
    # Filtres par credential
    credential_name = django_filters.CharFilter(
        field_name='credential__name',
        lookup_expr='icontains',
        help_text='Nom du credential (contient)'
    )
    
    credential_type = django_filters.CharFilter(
        field_name='credential__credential_type',
        help_text='Type de credential'
    )
    
    # Filtres spéciaux
    expiring_soon = django_filters.NumberFilter(
        method='filter_expiring_soon',
        help_text='Expire dans X jours'
    )
    
    class Meta:
        model = SharedCredential
        fields = []
    
    def filter_by_expiration(self, queryset, name, value):
        """Filtre par expiration"""
        now = timezone.now()
        if value:
            # Partagés expirés
            return queryset.filter(
                expires_at__lt=now,
                expires_at__isnull=False
            )
        else:
            # Partagés non expirés
            return queryset.filter(
                Q(expires_at__gte=now) | Q(expires_at__isnull=True)
            )
    
    def filter_by_status(self, queryset, name, value):
        """Filtre par statut global"""
        now = timezone.now()
        
        if value == 'active':
            return queryset.filter(
                is_active=True
            ).filter(
                Q(expires_at__gte=now) | Q(expires_at__isnull=True)
            )
        elif value == 'inactive':
            return queryset.filter(is_active=False)
        elif value == 'expired':
            return queryset.filter(
                is_active=True,
                expires_at__lt=now
            )
        
        return queryset
    
    def filter_expiring_soon(self, queryset, name, value):
        """Filtre les partages expirant bientôt"""
        if value is not None:
            from datetime import timedelta
            future_date = timezone.now() + timedelta(days=value)
            return queryset.filter(
                expires_at__lte=future_date,
                expires_at__gte=timezone.now(),
                is_active=True
            )
        return queryset


class SharedFolderFilter(django_filters.FilterSet):
    """
    Filtres pour les dossiers partagés
    """
    # Filtres par statut
    is_active = django_filters.BooleanFilter(
        field_name='is_active',
        help_text='Filtrer par statut actif/inactif'
    )
    
    is_expired = django_filters.BooleanFilter(
        method='filter_by_expiration',
        help_text='Filtrer par expiration'
    )
    
    status = django_filters.ChoiceFilter(
        choices=[
            ('active', 'Actif'),
            ('inactive', 'Inactif'),
            ('expired', 'Expiré'),
        ],
        method='filter_by_status',
        help_text='Filtrer par statut global'
    )
    
    # Filtres par permission
    permission = django_filters.ChoiceFilter(
        choices=[
            ('read', 'Lecture'),
            ('write', 'Écriture'),
            ('share', 'Partage'),
            ('admin', 'Admin'),
        ],
        help_text='Filtrer par niveau de permission'
    )
    
    # Filtres par dates
    shared_after = django_filters.DateTimeFilter(
        field_name='shared_at',
        lookup_expr='gte',
        help_text='Partagé après cette date'
    )
    
    shared_before = django_filters.DateTimeFilter(
        field_name='shared_at',
        lookup_expr='lte',
        help_text='Partagé avant cette date'
    )
    
    expires_after = django_filters.DateTimeFilter(
        field_name='expires_at',
        lookup_expr='gte',
        help_text='Expire après cette date'
    )
    
    expires_before = django_filters.DateTimeFilter(
        field_name='expires_at',
        lookup_expr='lte',
        help_text='Expire avant cette date'
    )
    
    # Filtres par utilisateur
    user_email = django_filters.CharFilter(
        field_name='user__email',
        lookup_expr='icontains',
        help_text='Email de l\'utilisateur (contient)'
    )
    
    shared_by_email = django_filters.CharFilter(
        field_name='shared_by__email',
        lookup_expr='icontains',
        help_text='Email de celui qui partage (contient)'
    )
    
    # Filtres par dossier
    folder_name = django_filters.CharFilter(
        field_name='folder__name',
        lookup_expr='icontains',
        help_text='Nom du dossier (contient)'
    )
    
    folder_color = django_filters.CharFilter(
        field_name='folder__color',
        help_text='Couleur du dossier'
    )
    
    # Filtres spéciaux
    expiring_soon = django_filters.NumberFilter(
        method='filter_expiring_soon',
        help_text='Expire dans X jours'
    )
    
    has_credentials = django_filters.BooleanFilter(
        method='filter_has_credentials',
        help_text='Dossiers avec/sans credentials'
    )
    
    class Meta:
        model = SharedFolder
        fields = []
    
    def filter_by_expiration(self, queryset, name, value):
        """Filtre par expiration"""
        now = timezone.now()
        if value:
            # Partagés expirés
            return queryset.filter(
                expires_at__lt=now,
                expires_at__isnull=False
            )
        else:
            # Partagés non expirés
            return queryset.filter(
                Q(expires_at__gte=now) | Q(expires_at__isnull=True)
            )
    
    def filter_by_status(self, queryset, name, value):
        """Filtre par statut global"""
        now = timezone.now()
        
        if value == 'active':
            return queryset.filter(
                is_active=True
            ).filter(
                Q(expires_at__gte=now) | Q(expires_at__isnull=True)
            )
        elif value == 'inactive':
            return queryset.filter(is_active=False)
        elif value == 'expired':
            return queryset.filter(
                is_active=True,
                expires_at__lt=now
            )
        
        return queryset
    
    def filter_expiring_soon(self, queryset, name, value):
        """Filtre les partages expirant bientôt"""
        if value is not None:
            from datetime import timedelta
            future_date = timezone.now() + timedelta(days=value)
            return queryset.filter(
                expires_at__lte=future_date,
                expires_at__gte=timezone.now(),
                is_active=True
            )
        return queryset
    
    def filter_has_credentials(self, queryset, name, value):
        """Filtre les dossiers avec ou sans credentials"""
        if value:
            return queryset.filter(folder__credentials__isnull=False).distinct()
        else:
            return queryset.filter(folder__credentials__isnull=True)