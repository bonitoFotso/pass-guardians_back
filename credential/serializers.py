# serializers.py
"""
Serializers pour les modèles de credentials avec gestion de la sécurité
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
import re

from .models import Category, Credential, PasswordHistory

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """Serializer pour les catégories"""
    credential_count = serializers.SerializerMethodField(read_only=True)
    icon_display = serializers.CharField(source='get_icon_display', read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'icon', 'icon_display', 'color', 
            'is_system', 'credential_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_credential_count(self, obj):
        """Retourne le nombre de credentials dans cette catégorie"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.credential_set.filter(owner=request.user).count()
        return obj.credential_set.count()
    
    def validate_color(self, value):
        """Valide le format hexadécimal de la couleur"""
        if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise serializers.ValidationError(
                "La couleur doit être au format hexadécimal (#RRGGBB)"
            )
        return value


class PasswordHistorySerializer(serializers.ModelSerializer):
    """Serializer pour l'historique des mots de passe"""
    
    class Meta:
        model = PasswordHistory
        fields = ['id', 'created_at']
        read_only_fields = ['id', 'created_at']


class CredentialListSerializer(serializers.ModelSerializer):
    """Serializer allégé pour la liste des credentials (sans données sensibles)"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True)
    has_password = serializers.SerializerMethodField()
    has_notes = serializers.SerializerMethodField()
    password_age_days = serializers.SerializerMethodField()
    last_used_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Credential
        fields = [
            'id', 'name', 'username', 'url', 'is_favorite', 'is_shared',
            'category', 'category_name', 'category_icon', 'category_color',
            'folder', 'folder_name', 'has_password', 'has_notes',
            'password_strength', 'password_age_days', 'last_used_at',
            'last_used_display', 'auto_generated', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_used_at',
            'password_strength', 'auto_generated'
        ]
    
    def get_has_password(self, obj):
        """Indique si le credential a un mot de passe"""
        return bool(obj.password_encrypted)
    
    def get_has_notes(self, obj):
        """Indique si le credential a des notes"""
        return bool(obj.notes_encrypted)
    
    def get_password_age_days(self, obj):
        """Retourne l'âge du mot de passe en jours"""
        if obj.password_changed_at:
            return (timezone.now() - obj.password_changed_at).days
        return None
    
    def get_last_used_display(self, obj):
        """Retourne un affichage formaté de la dernière utilisation"""
        if not obj.last_used_at:
            return "Jamais utilisé"
        
        now = timezone.now()
        diff = now - obj.last_used_at
        
        if diff.days == 0:
            return "Aujourd'hui"
        elif diff.days == 1:
            return "Hier"
        elif diff.days <= 7:
            return f"Il y a {diff.days} jours"
        elif diff.days <= 30:
            weeks = diff.days // 7
            return f"Il y a {weeks} semaine(s)"
        else:
            months = diff.days // 30
            return f"Il y a {months} mois"


class CredentialDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour les détails d'un credential"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    notes = serializers.CharField(write_only=True, required=False, allow_blank=True)
    decrypted_password = serializers.SerializerMethodField(read_only=True)
    decrypted_notes = serializers.SerializerMethodField(read_only=True)
    password_history = PasswordHistorySerializer(many=True, read_only=True)
    password_age_days = serializers.SerializerMethodField()
    
    class Meta:
        model = Credential
        fields = [
            'id', 'name', 'username', 'url', 'password', 'notes',
            'decrypted_password', 'decrypted_notes', 'is_favorite', 'is_shared',
            'category', 'category_name', 'category_icon', 'category_color',
            'folder', 'folder_name', 'password_strength', 'password_age_days',
            'password_changed_at', 'last_used_at', 'auto_generated',
            'password_history', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_used_at',
            'password_strength', 'password_changed_at', 'auto_generated'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'notes': {'write_only': True},
        }
    
    def get_decrypted_password(self, obj):
        """Retourne le mot de passe déchiffré"""
        # Seulement pour le propriétaire ou si partagé
        request = self.context.get('request')
        if request and request.user == obj.owner:
            return obj.decrypt_password()
        elif obj.is_shared:
            return obj.decrypt_password()
        return None
    
    def get_decrypted_notes(self, obj):
        """Retourne les notes déchiffrées"""
        request = self.context.get('request')
        if request and request.user == obj.owner:
            return obj.decrypt_notes()
        elif obj.is_shared:
            return obj.decrypt_notes()
        return None
    
    def get_password_age_days(self, obj):
        """Retourne l'âge du mot de passe en jours"""
        if obj.password_changed_at:
            return (timezone.now() - obj.password_changed_at).days
        return None
    
    def validate_url(self, value):
        """Valide l'URL si elle est fournie"""
        if value:
            validator = URLValidator()
            try:
                validator(value)
            except DjangoValidationError:
                raise serializers.ValidationError("URL invalide")
        return value
    
    def validate_password(self, value):
        """Valide la force du mot de passe"""
        if value:
            # Calculer la force du mot de passe
            strength = self._calculate_password_strength(value)
            if strength < 30:
                raise serializers.ValidationError(
                    "Le mot de passe est trop faible. Utilisez au moins 8 caractères "
                    "avec majuscules, minuscules, chiffres et caractères spéciaux."
                )
        return value
    
    def _calculate_password_strength(self, password):
        """Calcule la force d'un mot de passe (0-100)"""
        if not password:
            return 0
        
        score = 0
        length = len(password)
        
        # Longueur
        if length >= 8:
            score += 25
        if length >= 12:
            score += 10
        if length >= 16:
            score += 15
        
        # Caractères
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 20
        
        return min(score, 100)
    
    def create(self, validated_data):
        """Crée un nouveau credential avec chiffrement"""
        password = validated_data.pop('password', '')
        notes = validated_data.pop('notes', '')
        
        # Ajouter le propriétaire depuis le contexte
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['owner'] = request.user
        
        credential = Credential.objects.create(**validated_data)
        
        if password:
            credential.encrypt_password(password)
            credential.password_strength = self._calculate_password_strength(password)
            credential.password_changed_at = timezone.now()
        
        if notes:
            credential.encrypt_notes(notes)
        
        credential.save()
        return credential
    
    def update(self, instance, validated_data):
        """Met à jour un credential avec gestion du chiffrement"""
        password = validated_data.pop('password', None)
        notes = validated_data.pop('notes', None)
        
        # Vérifier les permissions
        request = self.context.get('request')
        if request and request.user != instance.owner and not instance.is_shared:
            raise serializers.ValidationError(
                "Vous n'avez pas la permission de modifier ce credential"
            )
        
        # Mettre à jour les champs normaux
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Gérer le mot de passe
        if password is not None:
            old_password = instance.decrypt_password()
            if password != old_password:
                instance.encrypt_password(password)
                instance.password_strength = self._calculate_password_strength(password)
                instance.password_changed_at = timezone.now()
        
        # Gérer les notes
        if notes is not None:
            instance.encrypt_notes(notes)
        
        instance.save()
        return instance


class CredentialCreateSerializer(serializers.ModelSerializer):
    """Serializer spécialisé pour la création de credentials"""
    password = serializers.CharField(write_only=True)
    notes = serializers.CharField(write_only=True, required=False, allow_blank=True)
    generate_password = serializers.BooleanField(write_only=True, required=False, default=False)
    password_length = serializers.IntegerField(write_only=True, required=False, default=16, min_value=8, max_value=128)
    include_symbols = serializers.BooleanField(write_only=True, required=False, default=True)
    
    class Meta:
        model = Credential
        fields = [
            'name', 'username', 'url', 'password', 'notes',
            'category', 'folder', 'is_favorite', 'is_shared',
            'generate_password', 'password_length', 'include_symbols'
        ]
    
    def validate(self, attrs):
        """Validation globale avec génération de mot de passe si demandée"""
        if attrs.get('generate_password'):
            # Générer un mot de passe automatiquement
            length = attrs.get('password_length', 16)
            include_symbols = attrs.get('include_symbols', True)
            attrs['password'] = self._generate_password(length, include_symbols)
            attrs['auto_generated'] = True
        
        return attrs
    
    def _generate_password(self, length, include_symbols):
        """Génère un mot de passe sécurisé"""
        import secrets
        import string
        
        characters = string.ascii_letters + string.digits
        if include_symbols:
            characters += "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        password = ''.join(secrets.choice(characters) for _ in range(length))
        
        # S'assurer qu'on a au moins un caractère de chaque type
        if not re.search(r'[a-z]', password):
            password = password[:-1] + secrets.choice(string.ascii_lowercase)
        if not re.search(r'[A-Z]', password):
            password = password[:-1] + secrets.choice(string.ascii_uppercase)
        if not re.search(r'\d', password):
            password = password[:-1] + secrets.choice(string.digits)
        if include_symbols and not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            password = password[:-1] + secrets.choice("!@#$%^&*")
        
        return password
    
    def create(self, validated_data):
        """Crée le credential avec les données nettoyées"""
        # Nettoyer les champs spécifiques à la génération
        generate_password = validated_data.pop('generate_password', False)
        password_length = validated_data.pop('password_length', None)
        include_symbols = validated_data.pop('include_symbols', None)
        
        # Utiliser le serializer de détail pour la création
        detail_serializer = CredentialDetailSerializer(context=self.context)
        return detail_serializer.create(validated_data)


class CredentialUpdateLastUsedSerializer(serializers.ModelSerializer):
    """Serializer pour mettre à jour seulement la date de dernière utilisation"""
    
    class Meta:
        model = Credential
        fields = ['last_used_at']
        read_only_fields = ['last_used_at']
    
    def update(self, instance, validated_data):
        """Met à jour la dernière utilisation"""
        instance.update_last_used()
        return instance