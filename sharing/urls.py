# urls.py
"""
URLs pour l'application de partage
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SharedCredentialViewSet,
    SharedFolderViewSet,
    MySharedCredentialsListView,
    MySharedFoldersListView,
    ShareCredentialView,
    ShareFolderView,
    RevokeCredentialShareView,
    RevokeFolderShareView,
    CleanupExpiredSharesView,
    ShareSummaryView
)

app_name = 'sharing'

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'sharing/shared-credentials', SharedCredentialViewSet, basename='shared-credentials')
router.register(r'sharing/shared-folders', SharedFolderViewSet, basename='shared-folders')

urlpatterns = [
    # URLs des ViewSets
    path('api/', include(router.urls)),
    
    # URLs pour les éléments partagés avec moi
    path('api/sharing/my-shared-credentials/', 
         MySharedCredentialsListView.as_view(), 
         name='my-shared-credentials'),

    path('api/sharing/my-shared-folders/', 
         MySharedFoldersListView.as_view(), 
         name='my-shared-folders'),
    
    # URLs pour partager des éléments spécifiques
    path('api/sharing/credentials/<uuid:credential_id>/share/', 
         ShareCredentialView.as_view(), 
         name='share-credential'),
    
    path('api/sharing/folders/<uuid:folder_id>/share/', 
         ShareFolderView.as_view(), 
         name='share-folder'),
    
    # URLs pour révoquer des partages
    path('api/sharing/credentials/<uuid:credential_id>/revoke/<int:user_id>/', 
         RevokeCredentialShareView.as_view(), 
         name='revoke-credential-share'),
    
    path('api/sharing/folders/<uuid:folder_id>/revoke/<int:user_id>/', 
         RevokeFolderShareView.as_view(), 
         name='revoke-folder-share'),
    
    # URLs utilitaires
    path('api/sharing/cleanup-expired/', 
         CleanupExpiredSharesView.as_view(), 
         name='cleanup-expired'),
    
    path('api/sharing/summary/', 
         ShareSummaryView.as_view(), 
         name='share-summary'),
]

'''
/api/shared-credentials/          # Liste et CRUD des partages credentials
/api/shared-folders/              # Liste et CRUD des partages dossiers
/api/my-shared-credentials/       # Credentials partagés avec moi
/api/my-shared-folders/           # Dossiers partagés avec moi
/api/credentials/{id}/share/      # Partager un credential
/api/folders/{id}/share/          # Partager un dossier
/api/credentials/{id}/revoke/{user_id}/  # Révoquer partage credential
/api/folders/{id}/revoke/{user_id}/      # Révoquer partage dossier
/api/cleanup-expired/             # Nettoyer les partages expirés
/api/summary/                     # Résumé des partages

'''