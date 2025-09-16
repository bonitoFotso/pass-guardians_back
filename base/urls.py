from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Configuration du router pour le ViewSet
router = DefaultRouter()
router.register(r'settings', views.AppSettingsViewSet, basename='appsettings')

urlpatterns = [
    # ===== APPROCHE 1: ViewSet avec Router (Recommandée) =====
    # URLs automatiques générées:
    # GET/POST     /api/settings/                  - Liste/Création
    # GET/PUT/PATCH/DELETE /api/settings/{id}/      - Détail/Modification/Suppression
    # GET          /api/settings/choices/          - Choix disponibles
    # POST         /api/settings/{id}/reset_to_default/ - Réinitialisation
    # GET          /api/settings/my_settings/      - Mes paramètres
    path('', include(router.urls)),
    
    # ===== APPROCHE 2: Vues génériques individuelles =====
    # Alternative si vous ne voulez pas utiliser le ViewSet
    path('', views.AppSettingsListCreateView.as_view(), name='settings-list-create'),
    path('<int:pk>/', views.AppSettingsRetrieveUpdateDestroyView.as_view(), name='settings-detail'),
    
    # ===== APPROCHE 3: Endpoints spécialisés pour l'utilisateur courant =====
    # Recommandé pour une interface utilisateur simple
    path('me/', views.UserSettingsView.as_view(), name='user-settings'),
    path('me/bulk-update/', views.AppSettingsBulkUpdateView.as_view(), name='user-settings-bulk'),
    path('me/export/', views.AppSettingsExportView.as_view(), name='user-settings-export'),
    
    # ===== Endpoints utilitaires =====
    path('choices/', views.AppSettingsChoicesView.as_view(), name='settings-choices'),
]

