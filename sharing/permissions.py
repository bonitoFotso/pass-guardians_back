# permissions.py
"""
Permissions personnalisées pour le système de partage
"""
from rest_framework import permissions


class IsOwnerOrSharedUser(permissions.BasePermission):
    """
    Permission pour les utilisateurs propriétaires ou ayant accès aux éléments partagés
    """
    
    def has_object_permission(self, request, view, obj):
        # Permissions de lecture pour les propriétaires et utilisateurs ayant accès
        if hasattr(obj, 'credential'):
            # Pour SharedCredential
            if obj.credential.owner == request.user:
                return True
            if obj.user == request.user and obj.is_active and not obj.is_expired:
                return request.method in permissions.SAFE_METHODS or obj.has_permission('write')
        
        elif hasattr(obj, 'folder'):
            # Pour SharedFolder
            if obj.folder.owner == request.user:
                return True
            if obj.user == request.user and obj.is_active and not obj.is_expired:
                return request.method in permissions.SAFE_METHODS or obj.has_permission('write')
        
        return False


class CanManageSharing(permissions.BasePermission):
    """
    Permission pour gérer les partages (créer, modifier, supprimer)
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Seul le propriétaire peut gérer les partages
        if hasattr(obj, 'credential'):
            return obj.credential.owner == request.user
        elif hasattr(obj, 'folder'):
            return obj.folder.owner == request.user
        return False


class CanShareCredential(permissions.BasePermission):
    """
    Permission pour partager un credential
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Vérifier si l'utilisateur peut partager le credential
        credential_id = view.kwargs.get('credential_id')
        if credential_id:
            from credential.models import Credential
            try:
                credential = Credential.objects.get(id=credential_id)
                return credential.owner == request.user
            except Credential.DoesNotExist:
                return False
        
        return True


class CanShareFolder(permissions.BasePermission):
    """
    Permission pour partager un dossier
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Vérifier si l'utilisateur peut partager le dossier
        folder_id = view.kwargs.get('folder_id')
        if folder_id:
            from folder.models import Folder
            try:
                folder = Folder.objects.get(id=folder_id)
                return folder.owner == request.user
            except Folder.DoesNotExist:
                return False
        
        return True


class CanAccessSharedContent(permissions.BasePermission):
    """
    Permission pour accéder au contenu partagé
    """
    
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Si c'est le propriétaire
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True
        
        # Si c'est un credential partagé
        if hasattr(obj, 'shared_with'):
            shared_credential = obj.shared_with.filter(
                user=request.user,
                is_active=True
            ).first()
            
            if shared_credential and not shared_credential.is_expired:
                if request.method in permissions.SAFE_METHODS:
                    return shared_credential.has_permission('read')
                else:
                    return shared_credential.has_permission('write')
        
        # Si c'est un dossier partagé
        if hasattr(obj, 'folder_shared_with'):
            shared_folder = obj.folder_shared_with.filter(
                user=request.user,
                is_active=True
            ).first()
            
            if shared_folder and not shared_folder.is_expired:
                if request.method in permissions.SAFE_METHODS:
                    return shared_folder.has_permission('read')
                else:
                    return shared_folder.has_permission('write')
        
        return False