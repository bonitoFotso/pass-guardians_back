from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import User
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer personnalisé pour JWT avec informations utilisateur"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Ajouter des informations personnalisées au token
        token['email'] = user.email
        token['full_name'] = user.full_name
        #token['is_verified'] = user.is_verified
        
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Ajouter des informations utilisateur à la réponse
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'username': self.user.username,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'full_name': self.user.full_name,
            #'is_verified': self.user.is_verified,
        }
        
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer pour l'inscription d'un nouvel utilisateur"""
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'password', 'password_confirm', 'phone'
        )

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password_confirm": "Les mots de passe ne correspondent pas."}
            )
        return attrs

    def create(self, validated_data):
        # Supprimer password_confirm des données validées
        validated_data.pop('password_confirm')
        
        # Créer l'utilisateur
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer pour le profil utilisateur"""
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'phone', 'avatar',
            'date_joined', 'last_login'
        )
        read_only_fields = ('id', 'email', 'date_joined', 'last_login')


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour la mise à jour du profil utilisateur"""

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone', 'avatar')


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer pour le changement de mot de passe"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Ancien mot de passe incorrect.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError(
                {"new_password_confirm": "Les nouveaux mots de passe ne correspondent pas."}
            )
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer pour la demande de réinitialisation de mot de passe"""
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Aucun utilisateur avec cette adresse email n'existe."
            )
        return value

class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model"""
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 
                  'is_active', 'date_joined', 'created_at', 'updated_at', 'full_name')
        read_only_fields = ('created_at', 'updated_at', 'date_joined')
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8}
        }

    def create(self, validated_data):
        """Create and return a new user with encrypted password"""
        return User.objects.create_user(**validated_data)
    
    def update(self, instance, validated_data):
        """Update a user, setting the password correctly"""
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        
        if password:
            user.set_password(password)
            user.save()
            
        return user

