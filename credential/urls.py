# urls.py
"""
Configuration des URLs pour l'application credentials
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    CategoryViewSet,
    CredentialViewSet,
    PasswordHistoryViewSet,
    check_password_breach
)

app_name = 'credentials'

# Router principal pour les ViewSets
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'credentials', CredentialViewSet, basename='credential')

# Router nested pour l'historique des mots de passe
credentials_router = routers.NestedDefaultRouter(router, r'credentials', lookup='credential')
credentials_router.register(r'history', PasswordHistoryViewSet, basename='credential-history')

urlpatterns = [
    # URLs des ViewSets (API REST complète)
    path('api/', include(router.urls)),
    path('api/', include(credentials_router.urls)),
    
    # URLs spécifiques pour les catégories
    path('api/categories/<int:pk>/credentials/', 
         CategoryViewSet.as_view({'get': 'credentials'}), 
         name='category-credentials'),
    path('api/categories/stats/', 
         CategoryViewSet.as_view({'get': 'stats'}), 
         name='category-stats'),
    
    # URLs spécifiques pour les credentials
    path('api/credentials-v/<uuid:pk>/mark-used/', 
         CredentialViewSet.as_view({'post': 'mark_used'}), 
         name='credential-mark-used'),
    path('api/credentials-v/<uuid:pk>/toggle-favorite/', 
         CredentialViewSet.as_view({'post': 'toggle_favorite'}), 
         name='credential-toggle-favorite'),
    path('api/credentials-v/<uuid:pk>/password-strength/', 
         CredentialViewSet.as_view({'get': 'password_strength'}), 
         name='credential-password-strength'),
    path('api/credentials-v/generate-password/', 
         CredentialViewSet.as_view({'post': 'generate_password'}), 
         name='credential-generate-password'),
    path('api/credentials-v/dashboard-stats/', 
         CredentialViewSet.as_view({'get': 'dashboard_stats'}), 
         name='credential-dashboard-stats'),
    path('api/credentials-v/export/', 
         CredentialViewSet.as_view({'get': 'export_data'}), 
         name='credential-export'),

    path('api/credentials-v/<uuid:pk>/reveal-password/',
         CredentialViewSet.as_view({'get': 'reveal_password'}),
         name='credential-reveal-password'),

    # URLs utilitaires
    path('api/credentials-v/<uuid:credential_id>/check-breach/', 
         check_password_breach, 
         name='credential-check-breach'),

    path('api/password/analyze/',
         CredentialViewSet.as_view({'post': 'analyze_password'}),
         name='credential-analyze'),
]

# URLs détaillées pour référence
"""
API Endpoints disponibles:

CATEGORIES:
- GET    /api/categories/                     - Liste des catégories
- POST   /api/categories/                     - Créer une catégorie
- GET    /api/categories/{id}/                - Détail d'une catégorie
- PUT    /api/categories/{id}/                - Modifier une catégorie
- PATCH  /api/categories/{id}/                - Modifier partiellement une catégorie
- DELETE /api/categories/{id}/                - Supprimer une catégorie
- GET    /api/categories/{id}/credentials/    - Credentials d'une catégorie
- GET    /api/categories/stats/               - Statistiques des catégories

CREDENTIALS:
- GET    /api/credentials-v/                    - Liste des credentials
- POST   /api/credentials-v/                    - Créer un credential
- GET    /api/credentials-v/{id}/               - Détail d'un credential
- PUT    /api/credentials-v/{id}/               - Modifier un credential
- PATCH  /api/credentials-v/{id}/               - Modifier partiellement un credential
- DELETE /api/credentials-v/{id}/               - Supprimer un credential
- POST   /api/credentials-v/{id}/mark-used/     - Marquer comme utilisé
- POST   /api/credentials-v/{id}/toggle-favorite/ - Basculer favori
- GET    /api/credentials-v/{id}/password-strength/ - Analyser la force du mot de passe
- POST   /api/credentials-v/generate-password/  - Générer un mot de passe
- GET    /api/credentials-v/dashboard-stats/    - Statistiques du tableau de bord
- GET    /api/credentials-v/export/             - Exporter les données

PASSWORD HISTORY:
- GET    /api/credentials-v/{id}/history/       - Historique des mots de passe d'un credential
- GET    /api/credentials-v/{id}/history/{history_id}/ - Détail d'un historique

UTILITIES:
- GET    /api/credentials-v/{id}/check-breach/  - Vérifier si le mot de passe est compromis

FILTRES DISPONIBLES:
- ?search=terme                              - Recherche textuelle
- ?category=id                               - Filtrer par catégorie
- ?folder=id                                 - Filtrer par dossier
- ?is_favorite=true                          - Filtrer les favoris
- ?weak_passwords=true                       - Filtrer les mots de passe faibles
- ?old_passwords=true                        - Filtrer les mots de passe anciens
- ?unused=true                               - Filtrer les credentials non utilisés
- ?ordering=field                            - Trier par champ
- ?page=n&page_size=20                       - Pagination

EXEMPLES D'UTILISATION:
- GET /api/credentials-v/?category=1&is_favorite=true
- GET /api/credentials-v/?search=google&ordering=-created_at
- GET /api/credentials-v/?weak_passwords=true&page=2
- POST /api/credentials-v/generate-password/ 
  {
    "length": 16,
    "include_symbols": true,
    "include_numbers": true,
    "include_uppercase": true,
    "include_lowercase": true,
    "exclude_ambiguous": false
  }
"""