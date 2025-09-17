# serializers.py
"""
Serializers pour les modèles de partage
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from .models import SharedCredential, SharedFolder
from credential.models import Credential
from credential.serializers import CredentialListSerializer
from folder.models import Folder
from folder.serializers import FolderListSerializer

User = get_user_model()


class UserMiniSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les utilisateurs"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'full_name']
        
    def get_full_name(self, obj):
        """Retourne le nom complet"""
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.username or obj.email


class SharedCredentialListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des credentials partagés"""
    credential_name = serializers.CharField(source='credential.name', read_only=True)
    credential_type = serializers.CharField(source='credential.credential_type', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    shared_by_email = serializers.EmailField(source='shared_by.email', read_only=True)
    is_expired = serializers.ReadOnlyField()
    status = serializers.SerializerMethodField()
    permission_display = serializers.SerializerMethodField()
    
    class Meta:
        model = SharedCredential
        fields = [
            'id', 'credential', 'credential_name', 'credential_type',
            'user', 'user_email', 'permission', 'permission_display',
            'shared_by', 'shared_by_email', 'shared_at', 'expires_at',
            'is_active', 'is_expired', 'status'
        ]
        
    def get_status(self, obj):
        """Retourne le statut du partage"""
        if not obj.is_active:
            return 'inactive'
        elif obj.is_expired:
            return 'expired'
        return 'active'
        
    def get_permission_display(self, obj):
        """Retourne le libellé de la permission"""
        permissions_map = {
            'read': 'Lecture seule',
            'write': 'Lecture et écriture',
            'share': 'Lecture, écriture et partage',
            'admin': 'Administration complète'
        }
        return permissions_map.get(obj.permission, obj.permission)


class SharedCredentialDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour les credentials partagés"""
    credential = CredentialListSerializer(read_only=True)
    user = UserMiniSerializer(read_only=True)
    shared_by = UserMiniSerializer(read_only=True)
    is_expired = serializers.ReadOnlyField()
    status = serializers.SerializerMethodField()
    permission_display = serializers.SerializerMethodField()
    permissions_details = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    
    class Meta:
        model = SharedCredential
        fields = [
            'id', 'credential', 'user', 'permission', 'permission_display',
            'shared_by', 'shared_at', 'expires_at', 'is_active',
            'is_expired', 'status', 'permissions_details', 'days_until_expiry'
        ]
        
    def get_status(self, obj):
        """Retourne le statut du partage"""
        if not obj.is_active:
            return 'inactive'
        elif obj.is_expired:
            return 'expired'
        return 'active'
        
    def get_permission_display(self, obj):
        """Retourne le libellé de la permission"""
        permissions_map = {
            'read': 'Lecture seule',
            'write': 'Lecture et écriture',
            'share': 'Lecture, écriture et partage',
            'admin': 'Administration complète'
        }
        return permissions_map.get(obj.permission, obj.permission)
        
    def get_permissions_details(self, obj):
        """Retourne les détails des permissions"""
        return {
            'can_read': obj.has_permission('read'),
            'can_write': obj.has_permission('write'),
            'can_share': obj.has_permission('share'),
            'can_admin': obj.has_permission('admin')
        }
        
    def get_days_until_expiry(self, obj):
        """Retourne le nombre de jours avant expiration"""
        if obj.expires_at:
            delta = obj.expires_at - timezone.now()
            return delta.days if delta.days > 0 else 0
        return None


class SharedCredentialCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer un partage de credential"""
    user_email = serializers.EmailField(write_only=True)
    expires_in_days = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = SharedCredential
        fields = [
            'user_email', 'permission',
            'expires_in_days', 'is_active'
        ]
        
    def validate_user_email(self, value):
        """Valide que l'utilisateur existe"""
        try:
            user = User.objects.get(email=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Aucun utilisateur trouvé avec cet email.")
            
    def validate(self, attrs):
        """Validations croisées"""
        # Récupérer le credential depuis le contexte de la requête
        credential_id = self.context.get('view').kwargs.get('credential_id')
        try:
            credential = Credential.objects.get(id=credential_id)
        except Credential.DoesNotExist:
            raise serializers.ValidationError("Credential non trouvé.")
            
        user_email = attrs.get('user_email')
        
        # Vérifier que l'utilisateur n'est pas le propriétaire
        user = User.objects.get(email=user_email)
        if credential.owner == user:
            raise serializers.ValidationError(
                "Vous ne pouvez pas partager un credential avec vous-même."
            )
            
        # Vérifier qu'un partage n'existe pas déjà
        if SharedCredential.objects.filter(
            credential=credential, 
            user=user
        ).exists():
            raise serializers.ValidationError(
                "Ce credential est déjà partagé avec cet utilisateur."
            )
        
        # Stocker le credential pour l'utiliser dans create()
        attrs['credential'] = credential
        return attrs
        
    def create(self, validated_data):
        """Crée le partage"""
        user_email = validated_data.pop('user_email')
        expires_in_days = validated_data.pop('expires_in_days', None)
        
        user = User.objects.get(email=user_email)
        validated_data['user'] = user
        validated_data['shared_by'] = self.context['request'].user
        
        if expires_in_days:
            validated_data['expires_at'] = timezone.now() + timedelta(days=expires_in_days)
            
        return super().create(validated_data)


class SharedFolderListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des dossiers partagés"""
    folder_name = serializers.CharField(source='folder.name', read_only=True)
    folder_color = serializers.CharField(source='folder.color', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    shared_by_email = serializers.EmailField(source='shared_by.email', read_only=True)
    is_expired = serializers.ReadOnlyField()
    status = serializers.SerializerMethodField()
    permission_display = serializers.SerializerMethodField()
    credentials_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SharedFolder
        fields = [
            'id', 'folder', 'folder_name', 'folder_color',
            'user', 'user_email', 'permission', 'permission_display',
            'shared_by', 'shared_by_email', 'shared_at', 'expires_at',
            'is_active', 'is_expired', 'status', 'credentials_count'
        ]
        
    def get_status(self, obj):
        """Retourne le statut du partage"""
        if not obj.is_active:
            return 'inactive'
        elif obj.is_expired:
            return 'expired'
        return 'active'
        
    def get_permission_display(self, obj):
        """Retourne le libellé de la permission"""
        permissions_map = {
            'read': 'Lecture seule',
            'write': 'Lecture et écriture',
            'share': 'Lecture, écriture et partage',
            'admin': 'Administration complète'
        }
        return permissions_map.get(obj.permission, obj.permission)
        
    def get_credentials_count(self, obj):
        """Retourne le nombre de credentials dans le dossier"""
        return obj.folder.credentials.count()


class SharedFolderDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour les dossiers partagés"""
    folder = FolderListSerializer(read_only=True)
    user = UserMiniSerializer(read_only=True)
    shared_by = UserMiniSerializer(read_only=True)
    is_expired = serializers.ReadOnlyField()
    status = serializers.SerializerMethodField()
    permission_display = serializers.SerializerMethodField()
    permissions_details = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    
    class Meta:
        model = SharedFolder
        fields = [
            'id', 'folder', 'user', 'permission', 'permission_display',
            'shared_by', 'shared_at', 'expires_at', 'is_active',
            'is_expired', 'status', 'permissions_details', 'days_until_expiry'
        ]
        
    def get_status(self, obj):
        """Retourne le statut du partage"""
        if not obj.is_active:
            return 'inactive'
        elif obj.is_expired:
            return 'expired'
        return 'active'
        
    def get_permission_display(self, obj):
        """Retourne le libellé de la permission"""
        permissions_map = {
            'read': 'Lecture seule',
            'write': 'Lecture et écriture',
            'share': 'Lecture, écriture et partage',
            'admin': 'Administration complète'
        }
        return permissions_map.get(obj.permission, obj.permission)
        
    def get_permissions_details(self, obj):
        """Retourne les détails des permissions"""
        return {
            'can_read': obj.has_permission('read'),
            'can_write': obj.has_permission('write'),
            'can_share': obj.has_permission('share'),
            'can_admin': obj.has_permission('admin')
        }
        
    def get_days_until_expiry(self, obj):
        """Retourne le nombre de jours avant expiration"""
        if obj.expires_at:
            delta = obj.expires_at - timezone.now()
            return delta.days if delta.days > 0 else 0
        return None


class SharedFolderCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer un partage de dossier"""
    user_email = serializers.EmailField(write_only=True)
    expires_in_days = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = SharedFolder
        fields = [
            'folder', 'user_email', 'permission',
            'expires_in_days', 'is_active'
        ]
        
    def validate_user_email(self, value):
        """Valide que l'utilisateur existe"""
        try:
            user = User.objects.get(email=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Aucun utilisateur trouvé avec cet email.")
            
    def validate(self, attrs):
        """Validations croisées"""
        folder = attrs.get('folder')
        user_email = attrs.get('user_email')
        
        # Vérifier que l'utilisateur n'est pas le propriétaire
        user = User.objects.get(email=user_email)
        if folder.owner == user:
            raise serializers.ValidationError(
                "Vous ne pouvez pas partager un dossier avec vous-même."
            )
            
        # Vérifier qu'un partage n'existe pas déjà
        if SharedFolder.objects.filter(
            folder=folder, 
            user=user
        ).exists():
            raise serializers.ValidationError(
                "Ce dossier est déjà partagé avec cet utilisateur."
            )
            
        return attrs
        
    def create(self, validated_data):
        """Crée le partage"""
        user_email = validated_data.pop('user_email')
        expires_in_days = validated_data.pop('expires_in_days', None)
        
        user = User.objects.get(email=user_email)
        validated_data['user'] = user
        validated_data['shared_by'] = self.context['request'].user
        
        if expires_in_days:
            validated_data['expires_at'] = timezone.now() + timedelta(days=expires_in_days)
            
        return super().create(validated_data)


class SharedCredentialUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour mettre à jour un partage de credential"""
    
    class Meta:
        model = SharedCredential
        fields = ['permission', 'expires_at', 'is_active']
        
    def validate_expires_at(self, value):
        """Valide que la date d'expiration est future"""
        if value and value <= timezone.now():
            raise serializers.ValidationError(
                "La date d'expiration doit être dans le futur."
            )
        return value


class SharedFolderUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour mettre à jour un partage de dossier"""
    
    class Meta:
        model = SharedFolder
        fields = ['permission', 'expires_at', 'is_active']
        
    def validate_expires_at(self, value):
        """Valide que la date d'expiration est future"""
        if value and value <= timezone.now():
            raise serializers.ValidationError(
                "La date d'expiration doit être dans le futur."
            )
        return value


# Serializers pour les listes des éléments partagés avec l'utilisateur connecté
class MySharedCredentialsSerializer(serializers.ModelSerializer):
    """Serializer pour les credentials partagés avec moi"""
    credential = CredentialListSerializer(read_only=True)
    shared_by = UserMiniSerializer(read_only=True)
    permission_display = serializers.SerializerMethodField()
    permissions_details = serializers.SerializerMethodField()
    
    class Meta:
        model = SharedCredential
        fields = [
            'id', 'credential', 'permission', 'permission_display',
            'shared_by', 'shared_at', 'expires_at', 'permissions_details'
        ]
        
    def get_permission_display(self, obj):
        """Retourne le libellé de la permission"""
        permissions_map = {
            'read': 'Lecture seule',
            'write': 'Lecture et écriture',
            'share': 'Lecture, écriture et partage',
            'admin': 'Administration complète'
        }
        return permissions_map.get(obj.permission, obj.permission)
        
    def get_permissions_details(self, obj):
        """Retourne les détails des permissions"""
        return {
            'can_read': obj.has_permission('read'),
            'can_write': obj.has_permission('write'),
            'can_share': obj.has_permission('share'),
            'can_admin': obj.has_permission('admin')
        }


class MySharedFoldersSerializer(serializers.ModelSerializer):
    """Serializer pour les dossiers partagés avec moi"""
    folder = FolderListSerializer(read_only=True)
    shared_by = UserMiniSerializer(read_only=True)
    permission_display = serializers.SerializerMethodField()
    permissions_details = serializers.SerializerMethodField()
    
    class Meta:
        model = SharedFolder
        fields = [
            'id', 'folder', 'permission', 'permission_display',
            'shared_by', 'shared_at', 'expires_at', 'permissions_details'
        ]
        
    def get_permission_display(self, obj):
        """Retourne le libellé de la permission"""
        permissions_map = {
            'read': 'Lecture seule',
            'write': 'Lecture et écriture',
            'share': 'Lecture, écriture et partage',
            'admin': 'Administration complète'
        }
        return permissions_map.get(obj.permission, obj.permission)
        
    def get_permissions_details(self, obj):
        """Retourne les détails des permissions"""
        return {
            'can_read': obj.has_permission('read'),
            'can_write': obj.has_permission('write'),
            'can_share': obj.has_permission('share'),
            'can_admin': obj.has_permission('admin')
        }