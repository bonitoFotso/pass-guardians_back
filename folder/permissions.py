# permissions.py
"""
Permissions personnalisées pour les dossiers
"""
from rest_framework.permissions import BasePermission


class IsFolderOwner(BasePermission):
    """
    Permission personnalisée pour s'assurer que seul le propriétaire
    du dossier peut le modifier/supprimer
    """
    
    def has_object_permission(self, request, view, obj):
        """
        Vérifier que l'utilisateur est le propriétaire du dossier
        """
        return obj.owner == request.user


class CanViewSharedFolder(BasePermission):
    """
    Permission pour voir les dossiers partagés
    """
    
    def has_object_permission(self, request, view, obj):
        """
        Autoriser la lecture si le dossier est partagé ou appartient à l'utilisateur
        """
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return obj.is_shared or obj.owner == request.user
        
        # Pour les autres méthodes, seul le propriétaire peut agir
        return obj.owner == request.user