from rest_framework import viewsets, permissions
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import Technicien
from .serializers import UserSerializer
from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, extend_schema_view

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Vue personnalisée pour l'obtention du token JWT"""
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema_view(
    create=extend_schema(
        summary="Inscription d'un nouvel utilisateur",
        description="Créer un nouveau compte utilisateur"
    ),
    retrieve=extend_schema(
        summary="Profil utilisateur",
        description="Récupérer les informations du profil utilisateur connecté"
    ),
    partial_update=extend_schema(
        summary="Mise à jour du profil",
        description="Mettre à jour les informations du profil utilisateur"
    ),
)
class AuthViewSet(CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    """ViewSet pour la gestion de l'authentification et des profils utilisateur"""
    queryset = User.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegistrationSerializer
        elif self.action in ['retrieve', 'list']:
            return UserProfileSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'change_password':
            return PasswordChangeSerializer
        elif self.action == 'request_password_reset':
            return PasswordResetRequestSerializer
        return UserProfileSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        elif self.action == 'request_password_reset':
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_object(self):
        """Retourne toujours l'utilisateur connecté pour les actions de profil"""
        if self.action in ['retrieve', 'update', 'partial_update', 'change_password']:
            return self.request.user
        return super().get_object()

    def create(self, request, *args, **kwargs):
        """Inscription d'un nouvel utilisateur"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response(
            {
                'message': 'Utilisateur créé avec succès',
                'user': UserProfileSerializer(user).data
            },
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary="Changer le mot de passe",
        description="Changer le mot de passe de l'utilisateur connecté"
    )
    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """Changer le mot de passe de l'utilisateur connecté"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {'message': 'Mot de passe modifié avec succès'},
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Demande de réinitialisation de mot de passe",
        description="Envoyer un email de réinitialisation de mot de passe"
    )
    @action(detail=False, methods=['post'], url_path='request-password-reset')
    def request_password_reset(self, request):
        """Demander la réinitialisation du mot de passe"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Ici vous pouvez ajouter la logique d'envoi d'email
        # Par exemple avec Celery pour l'envoi asynchrone
        
        return Response(
            {'message': 'Email de réinitialisation envoyé'},
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Informations utilisateur connecté",
        description="Récupérer les informations de l'utilisateur connecté"
    )
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Retourne les informations de l'utilisateur connecté"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Users
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


