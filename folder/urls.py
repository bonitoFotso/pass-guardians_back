# urls.py
"""
URLs pour l'application de gestion des dossiers
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'folders'

# Router pour le ViewSet
router = DefaultRouter()
router.register(r'folders', views.FolderViewSet, basename='folder')

urlpatterns = [
    # URLs du ViewSet (avec toutes les actions personnalisées)
    path('', include(router.urls)),
    
    # URLs alternatives avec vues génériques (optionnel)
    path('folders-list/', views.FolderListCreateView.as_view(), name='folder-list-create'),
    path('folders-detail/<int:pk>/', views.FolderDetailView.as_view(), name='folder-detail'),
    path('folders-tree/', views.FolderTreeView.as_view(), name='folder-tree'),
    path('folders-shared/', views.SharedFolderListView.as_view(), name='shared-folders'),
    path('folders-stats/', views.FolderStatsView.as_view(), name='folder-stats'),
]

"""
URLs générées automatiquement par le ViewSet :

MÉTHODES STANDARD :
- GET    /api/v1/folders/                    # Liste des dossiers
- POST   /api/v1/folders/                    # Créer un dossier
- GET    /api/v1/folders/{id}/               # Détail d'un dossier
- PUT    /api/v1/folders/{id}/               # Modifier un dossier (complet)
- PATCH  /api/v1/folders/{id}/               # Modifier un dossier (partiel)
- DELETE /api/v1/folders/{id}/               # Supprimer un dossier

ACTIONS PERSONNALISÉES :
- GET    /api/v1/folders/tree/               # Arborescence complète
- GET    /api/v1/folders/roots/              # Dossiers racine seulement
- GET    /api/v1/folders/{id}/children/      # Enfants directs
- GET    /api/v1/folders/{id}/descendants/   # Tous les descendants
- GET    /api/v1/folders/{id}/breadcrumbs/   # Chemin de navigation
- POST   /api/v1/folders/{id}/move/          # Déplacer un dossier
- POST   /api/v1/folders/{id}/duplicate/     # Dupliquer un dossier

URLS SUPPLÉMENTAIRES :
- GET    /api/v1/folders-shared/             # Dossiers partagés
- GET    /api/v1/folders-stats/              # Statistiques utilisateur
"""