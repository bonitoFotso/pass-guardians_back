# serializers.py
"""
Serializers pour les dossiers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Folder

User = get_user_model()


class FolderListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des dossiers (lecture seule, optimisé)"""
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    children_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Folder
        fields = [
            'id', 'name', 'color', 'is_shared', 
            'owner_email', 'parent', 'parent_name',
            'children_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_children_count(self, obj):
        """Retourne le nombre d'enfants directs"""
        return obj.children.count()


class FolderDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un dossier"""
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_path = serializers.ReadOnlyField()
    children = serializers.SerializerMethodField()
    descendants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Folder
        fields = [
            'id', 'name', 'color', 'is_shared',
            'owner', 'owner_email', 'parent', 'parent_name',
            'full_path', 'children', 'descendants_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 'full_path']
    
    def get_children(self, obj):
        """Retourne les dossiers enfants directs"""
        children = obj.children.all().order_by('name')
        return FolderListSerializer(children, many=True).data
    
    def get_descendants_count(self, obj):
        """Retourne le nombre total de descendants"""
        return len(obj.get_descendants())


class FolderCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification de dossiers"""
    
    class Meta:
        model = Folder
        fields = ['name', 'parent', 'color', 'is_shared']
    
    def validate(self, data):
        """Validations personnalisées"""
        # Récupérer l'utilisateur depuis le contexte
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Utilisateur non authentifié")
        
        owner = request.user
        name = data.get('name')
        parent = data.get('parent')
        
        # Vérifier l'unicité du nom dans le même dossier parent pour le même propriétaire
        queryset = Folder.objects.filter(
            name=name,
            parent=parent,
            owner=owner
        )
        
        # Exclure l'instance actuelle en cas de modification
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError({
                'name': 'Un dossier avec ce nom existe déjà dans ce répertoire.'
            })
        
        # Vérifier que le parent appartient au même utilisateur
        if parent and parent.owner != owner:
            raise serializers.ValidationError({
                'parent': 'Le dossier parent doit vous appartenir.'
            })
        
        # Éviter les références circulaires
        if self.instance and parent:
            if parent == self.instance:
                raise serializers.ValidationError({
                    'parent': 'Un dossier ne peut pas être son propre parent.'
                })
            
            # Vérifier que le parent n'est pas un descendant
            descendants = self.instance.get_descendants()
            if parent in descendants:
                raise serializers.ValidationError({
                    'parent': 'Référence circulaire détectée. Le dossier parent ne peut pas être un descendant.'
                })
        
        return data
    
    def create(self, validated_data):
        """Création d'un nouveau dossier"""
        request = self.context.get('request')
        validated_data['owner'] = request.user
        return super().create(validated_data)


class FolderTreeSerializer(serializers.ModelSerializer):
    """Serializer pour l'affichage en arbre (récursif)"""
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Folder
        fields = ['id', 'name', 'color', 'is_shared', 'children']
    
    def get_children(self, obj):
        """Récupère récursivement tous les enfants"""
        children = obj.children.all().order_by('name')
        return FolderTreeSerializer(children, many=True, context=self.context).data


class FolderMoveSerializer(serializers.Serializer):
    """Serializer pour déplacer un dossier"""
    new_parent_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_new_parent_id(self, value):
        """Valide le nouveau parent"""
        if value is None:
            return None
        
        try:
            new_parent = Folder.objects.get(id=value)
        except Folder.DoesNotExist:
            raise serializers.ValidationError("Le dossier parent spécifié n'existe pas.")
        
        # Vérifier que le nouveau parent appartient au même utilisateur
        request = self.context.get('request')
        if new_parent.owner != request.user:
            raise serializers.ValidationError("Le nouveau dossier parent doit vous appartenir.")
        
        return value
    
    def validate(self, data):
        """Validations pour éviter les références circulaires"""
        folder = self.context.get('folder')  # Dossier à déplacer
        new_parent_id = data.get('new_parent_id')
        
        if new_parent_id:
            new_parent = Folder.objects.get(id=new_parent_id)
            
            # Éviter l'auto-référence
            if new_parent == folder:
                raise serializers.ValidationError({
                    'new_parent_id': 'Un dossier ne peut pas être son propre parent.'
                })
            
            # Éviter les références circulaires
            descendants = folder.get_descendants()
            if new_parent in descendants:
                raise serializers.ValidationError({
                    'new_parent_id': 'Référence circulaire détectée.'
                })
        
        return data


class FolderBreadcrumbSerializer(serializers.ModelSerializer):
    """Serializer pour les breadcrumbs (chemin de navigation)"""
    
    class Meta:
        model = Folder
        fields = ['id', 'name']
    
    @classmethod
    def get_breadcrumbs(cls, folder):
        """Retourne la liste des dossiers parents jusqu'à la racine"""
        breadcrumbs = []
        current = folder
        
        while current:
            breadcrumbs.insert(0, cls(current).data)
            current = current.parent
        
        return breadcrumbs