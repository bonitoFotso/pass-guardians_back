# views.py
"""
Vues DRF pour les modèles de partage
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import SharedCredential, SharedFolder
from .serializers import (
    SharedCredentialListSerializer,
    SharedCredentialDetailSerializer,
    SharedCredentialCreateSerializer,
    SharedCredentialUpdateSerializer,
    SharedFolderListSerializer,
    SharedFolderDetailSerializer,
    SharedFolderCreateSerializer,
    SharedFolderUpdateSerializer,
    MySharedCredentialsSerializer,
    MySharedFoldersSerializer
)
from .permissions import IsOwnerOrSharedUser, CanManageSharing
from .filters import SharedCredentialFilter, SharedFolderFilter
from credential.models import Credential
from folder.models import Folder


class SharedCredentialViewSet(ModelViewSet):
    """
    ViewSet pour gérer les partages de credentials
    """
    permission_classes = [IsAuthenticated, CanManageSharing]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SharedCredentialFilter
    search_fields = ['credential__name', 'user__email', 'user__username']
    ordering_fields = ['shared_at', 'expires_at', 'permission']
    ordering = ['-shared_at']
    
    def get_queryset(self):
        """Retourne les partages où l'utilisateur est propriétaire du credential"""
        return SharedCredential.objects.filter(
            credential__owner=self.request.user
        ).select_related(
            'credential', 'user', 'shared_by'
        ).prefetch_related(
            'credential__folder'
        )
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'list':
            return SharedCredentialListSerializer
        elif self.action == 'create':
            return SharedCredentialCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SharedCredentialUpdateSerializer
        return SharedCredentialDetailSerializer
    
    def perform_create(self, serializer):
        """Associe l'utilisateur connecté comme celui qui partage"""
        serializer.save(shared_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def extend_expiration(self, request, pk=None):
        """Étend l'expiration du partage"""
        shared_credential = self.get_object()
        days = request.data.get('days', 30)
        
        try:
            days = int(days)
            if days <= 0 or days > 365:
                return Response(
                    {'error': 'Le nombre de jours doit être entre 1 et 365'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Nombre de jours invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from datetime import timedelta
        if shared_credential.expires_at:
            shared_credential.expires_at += timedelta(days=days)
        else:
            shared_credential.expires_at = timezone.now() + timedelta(days=days)
        
        shared_credential.save()
        
        serializer = self.get_serializer(shared_credential)
        return Response({
            'message': f'Expiration étendue de {days} jours',
            'shared_credential': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Active/désactive le partage"""
        shared_credential = self.get_object()
        shared_credential.is_active = not shared_credential.is_active
        shared_credential.save()
        
        status_text = 'activé' if shared_credential.is_active else 'désactivé'
        serializer = self.get_serializer(shared_credential)
        
        return Response({
            'message': f'Partage {status_text}',
            'shared_credential': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques des partages de l'utilisateur"""
        queryset = self.get_queryset()
        
        total = queryset.count()
        active = queryset.filter(is_active=True).count()
        expired = queryset.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        ).count()
        
        by_permission = queryset.values('permission').annotate(
            count=Count('id')
        ).order_by('permission')
        
        return Response({
            'total_shared': total,
            'active_shares': active,
            'expired_shares': expired,
            'inactive_shares': total - active,
            'by_permission': list(by_permission)
        })


class SharedFolderViewSet(ModelViewSet):
    """
    ViewSet pour gérer les partages de dossiers
    """
    permission_classes = [IsAuthenticated, CanManageSharing]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SharedFolderFilter
    search_fields = ['folder__name', 'user__email', 'user__username']
    ordering_fields = ['shared_at', 'expires_at', 'permission']
    ordering = ['-shared_at']
    
    def get_queryset(self):
        """Retourne les partages où l'utilisateur est propriétaire du dossier"""
        return SharedFolder.objects.filter(
            folder__owner=self.request.user
        ).select_related(
            'folder', 'user', 'shared_by'
        ).prefetch_related(
            'folder__credentials'
        )
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'list':
            return SharedFolderListSerializer
        elif self.action == 'create':
            return SharedFolderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SharedFolderUpdateSerializer
        return SharedFolderDetailSerializer
    
    def perform_create(self, serializer):
        """Associe l'utilisateur connecté comme celui qui partage"""
        serializer.save(shared_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def extend_expiration(self, request, pk=None):
        """Étend l'expiration du partage"""
        shared_folder = self.get_object()
        days = request.data.get('days', 30)
        
        try:
            days = int(days)
            if days <= 0 or days > 365:
                return Response(
                    {'error': 'Le nombre de jours doit être entre 1 et 365'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Nombre de jours invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from datetime import timedelta
        if shared_folder.expires_at:
            shared_folder.expires_at += timedelta(days=days)
        else:
            shared_folder.expires_at = timezone.now() + timedelta(days=days)
        
        shared_folder.save()
        
        serializer = self.get_serializer(shared_folder)
        return Response({
            'message': f'Expiration étendue de {days} jours',
            'shared_folder': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Active/désactive le partage"""
        shared_folder = self.get_object()
        shared_folder.is_active = not shared_folder.is_active
        shared_folder.save()
        
        status_text = 'activé' if shared_folder.is_active else 'désactivé'
        serializer = self.get_serializer(shared_folder)
        
        return Response({
            'message': f'Partage {status_text}',
            'shared_folder': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques des partages de l'utilisateur"""
        queryset = self.get_queryset()
        
        total = queryset.count()
        active = queryset.filter(is_active=True).count()
        expired = queryset.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        ).count()
        
        by_permission = queryset.values('permission').annotate(
            count=Count('id')
        ).order_by('permission')
        
        return Response({
            'total_shared': total,
            'active_shares': active,
            'expired_shares': expired,
            'inactive_shares': total - active,
            'by_permission': list(by_permission)
        })


class MySharedCredentialsListView(generics.ListAPIView):
    """
    Liste des credentials partagés avec l'utilisateur connecté
    """
    serializer_class = MySharedCredentialsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['credential__name', 'shared_by__email']
    ordering_fields = ['shared_at', 'expires_at']
    ordering = ['-shared_at']
    
    def get_queryset(self):
        """Retourne les credentials partagés avec l'utilisateur connecté"""
        return SharedCredential.objects.filter(
            user=self.request.user,
            is_active=True
        ).exclude(
            expires_at__lt=timezone.now()
        ).select_related(
            'credential', 'shared_by', 'credential__owner'
        ).prefetch_related(
            'credential__folder'
        )


class MySharedFoldersListView(generics.ListAPIView):
    """
    Liste des dossiers partagés avec l'utilisateur connecté
    """
    serializer_class = MySharedFoldersSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['folder__name', 'shared_by__email']
    ordering_fields = ['shared_at', 'expires_at']
    ordering = ['-shared_at']
    
    def get_queryset(self):
        """Retourne les dossiers partagés avec l'utilisateur connecté"""
        return SharedFolder.objects.filter(
            user=self.request.user,
            is_active=True
        ).exclude(
            expires_at__lt=timezone.now()
        ).select_related(
            'folder', 'shared_by', 'folder__owner'
        ).prefetch_related(
            'folder__credentials'
        )


class ShareCredentialView(generics.CreateAPIView):
    """
    Vue pour partager un credential spécifique
    """
    serializer_class = SharedCredentialCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        """Vérifie que l'utilisateur peut partager ce credential"""
        credential_id = self.kwargs.get('credential_id')
        credential = get_object_or_404(
            Credential,
            id=credential_id,
            owner=self.request.user
        )
        print(credential)
        serializer.save(credential=credential, shared_by=self.request.user)


class ShareFolderView(generics.CreateAPIView):
    """
    Vue pour partager un dossier spécifique
    """
    serializer_class = SharedFolderCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        """Vérifie que l'utilisateur peut partager ce dossier"""
        folder_id = self.kwargs.get('folder_id')
        folder = get_object_or_404(
            Folder,
            id=folder_id,
            owner=self.request.user
        )
        serializer.save(folder=folder, shared_by=self.request.user)


class RevokeCredentialShareView(generics.DestroyAPIView):
    """
    Vue pour révoquer un partage de credential
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Récupère le partage à révoquer"""
        credential_id = self.kwargs.get('credential_id')
        user_id = self.kwargs.get('user_id')
        
        return get_object_or_404(
            SharedCredential,
            credential_id=credential_id,
            user_id=user_id,
            credential__owner=self.request.user
        )
    
    def destroy(self, request, *args, **kwargs):
        """Supprime le partage"""
        instance = self.get_object()
        instance.delete()
        return Response({
            'message': 'Partage révoqué avec succès'
        }, status=status.HTTP_200_OK)


class RevokeFolderShareView(generics.DestroyAPIView):
    """
    Vue pour révoquer un partage de dossier
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Récupère le partage à révoquer"""
        folder_id = self.kwargs.get('folder_id')
        user_id = self.kwargs.get('user_id')
        
        return get_object_or_404(
            SharedFolder,
            folder_id=folder_id,
            user_id=user_id,
            folder__owner=self.request.user
        )
    
    def destroy(self, request, *args, **kwargs):
        """Supprime le partage"""
        instance = self.get_object()
        instance.delete()
        return Response({
            'message': 'Partage révoqué avec succès'
        }, status=status.HTTP_200_OK)


class CleanupExpiredSharesView(generics.GenericAPIView):
    """
    Vue pour nettoyer les partages expirés (action admin)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Désactive les partages expirés"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission refusée'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        now = timezone.now()
        
        # Désactiver les credentials partagés expirés
        expired_credentials = SharedCredential.objects.filter(
            expires_at__lt=now,
            is_active=True
        ).update(is_active=False)
        
        # Désactiver les dossiers partagés expirés
        expired_folders = SharedFolder.objects.filter(
            expires_at__lt=now,
            is_active=True
        ).update(is_active=False)
        
        return Response({
            'message': 'Nettoyage terminé',
            'expired_credentials': expired_credentials,
            'expired_folders': expired_folders
        })


class ShareSummaryView(generics.GenericAPIView):
    """
    Vue pour obtenir un résumé des partages de l'utilisateur
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Retourne un résumé des partages"""
        user = request.user
        
        # Credentials que j'ai partagés
        shared_credentials = SharedCredential.objects.filter(
            credential__owner=user
        ).aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            expired=Count('id', filter=Q(expires_at__lt=timezone.now(), is_active=True))
        )
        
        # Dossiers que j'ai partagés
        shared_folders = SharedFolder.objects.filter(
            folder__owner=user
        ).aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            expired=Count('id', filter=Q(expires_at__lt=timezone.now(), is_active=True))
        )
        
        # Credentials partagés avec moi
        shared_with_me_credentials = SharedCredential.objects.filter(
            user=user,
            is_active=True
        ).exclude(
            expires_at__lt=timezone.now()
        ).count()
        
        # Dossiers partagés avec moi
        shared_with_me_folders = SharedFolder.objects.filter(
            user=user,
            is_active=True
        ).exclude(
            expires_at__lt=timezone.now()
        ).count()
        
        return Response({
            'shared_by_me': {
                'credentials': shared_credentials,
                'folders': shared_folders
            },
            'shared_with_me': {
                'credentials': shared_with_me_credentials,
                'folders': shared_with_me_folders
            }
        })