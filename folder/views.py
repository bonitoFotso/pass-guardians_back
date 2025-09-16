# views.py
"""
Vues DRF pour la gestion des dossiers
"""
from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404

from .models import Folder
from .serializers import (
    FolderListSerializer,
    FolderDetailSerializer,
    FolderCreateUpdateSerializer,
    FolderTreeSerializer,
    FolderMoveSerializer,
    FolderBreadcrumbSerializer
)
from .permissions import IsFolderOwner


class FolderViewSet(ModelViewSet):
    """ViewSet complet pour la gestion des dossiers"""
    
    permission_classes = [IsAuthenticated, IsFolderOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['color', 'is_shared', 'parent']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Retourne seulement les dossiers de l'utilisateur connecté"""
        return Folder.objects.filter(owner=self.request.user).select_related(
            'owner', 'parent'
        ).prefetch_related('children')
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'list':
            return FolderListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return FolderCreateUpdateSerializer
        elif self.action == 'tree':
            return FolderTreeSerializer
        elif self.action == 'move':
            return FolderMoveSerializer
        else:
            return FolderDetailSerializer
    
    def perform_create(self, serializer):
        """Assigne automatiquement le propriétaire lors de la création"""
        serializer.save(owner=self.request.user)
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Retourne l'arborescence complète des dossiers"""
        # Récupérer seulement les dossiers racine (sans parent)
        root_folders = self.get_queryset().filter(parent=None)
        serializer = self.get_serializer(root_folders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def roots(self, request):
        """Retourne seulement les dossiers racine"""
        root_folders = self.get_queryset().filter(parent=None)
        serializer = FolderListSerializer(root_folders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """Retourne les enfants directs d'un dossier"""
        folder = self.get_object()
        children = folder.children.all().order_by('name')
        serializer = FolderListSerializer(children, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def descendants(self, request, pk=None):
        """Retourne tous les descendants d'un dossier"""
        folder = self.get_object()
        descendants = folder.get_descendants()
        serializer = FolderListSerializer(descendants, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def breadcrumbs(self, request, pk=None):
        """Retourne le chemin de navigation (breadcrumbs)"""
        folder = self.get_object()
        breadcrumbs = FolderBreadcrumbSerializer.get_breadcrumbs(folder)
        return Response(breadcrumbs)
    
    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """Déplace un dossier vers un nouveau parent"""
        folder = self.get_object()
        serializer = FolderMoveSerializer(
            data=request.data,
            context={'request': request, 'folder': folder}
        )
        
        if serializer.is_valid():
            new_parent_id = serializer.validated_data.get('new_parent_id')
            new_parent = None
            
            if new_parent_id:
                new_parent = get_object_or_404(
                    Folder, 
                    id=new_parent_id, 
                    owner=request.user
                )
            
            # Vérifier l'unicité du nom dans le nouveau répertoire
            existing = Folder.objects.filter(
                name=folder.name,
                parent=new_parent,
                owner=request.user
            ).exclude(pk=folder.pk)
            
            if existing.exists():
                return Response(
                    {'error': 'Un dossier avec ce nom existe déjà dans le répertoire de destination.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            folder.parent = new_parent
            folder.save()
            
            serializer = FolderDetailSerializer(folder)
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplique un dossier (avec un nouveau nom)"""
        original_folder = self.get_object()
        new_name = request.data.get('name', f"{original_folder.name} (copie)")
        
        # Vérifier l'unicité du nouveau nom
        if Folder.objects.filter(
            name=new_name,
            parent=original_folder.parent,
            owner=request.user
        ).exists():
            return Response(
                {'error': 'Un dossier avec ce nom existe déjà.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer la copie
        new_folder = Folder.objects.create(
            name=new_name,
            parent=original_folder.parent,
            owner=request.user,
            color=original_folder.color,
            is_shared=original_folder.is_shared
        )
        
        serializer = FolderDetailSerializer(new_folder)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FolderListCreateView(generics.ListCreateAPIView):
    """Vue pour lister et créer des dossiers"""
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['color', 'is_shared', 'parent']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        queryset = Folder.objects.filter(owner=self.request.user).select_related(
            'owner', 'parent'
        ).annotate(children_count=Count('children'))
        
        # Filtre par parent depuis l'URL
        parent_id = self.request.query_params.get('parent_id')
        if parent_id:
            if parent_id == 'null':
                queryset = queryset.filter(parent=None)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FolderCreateUpdateSerializer
        return FolderListSerializer
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class FolderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Vue détaillée pour un dossier"""
    
    permission_classes = [IsAuthenticated, IsFolderOwner]
    
    def get_queryset(self):
        return Folder.objects.filter(owner=self.request.user).select_related(
            'owner', 'parent'
        ).prefetch_related('children')
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return FolderCreateUpdateSerializer
        return FolderDetailSerializer


class FolderTreeView(generics.ListAPIView):
    """Vue pour l'arborescence complète"""
    
    serializer_class = FolderTreeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Retourne seulement les dossiers racine avec tous leurs enfants
        return Folder.objects.filter(
            owner=self.request.user, 
            parent=None
        ).prefetch_related(
            Prefetch(
                'children',
                queryset=Folder.objects.select_related('owner').order_by('name')
            )
        ).order_by('name')


class SharedFolderListView(generics.ListAPIView):
    """Vue pour les dossiers partagés"""
    
    serializer_class = FolderListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'owner__email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        return Folder.objects.filter(
            is_shared=True
        ).select_related('owner', 'parent').annotate(
            children_count=Count('children')
        )


class FolderStatsView(generics.GenericAPIView):
    """Vue pour les statistiques des dossiers"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Retourne les statistiques des dossiers de l'utilisateur"""
        queryset = Folder.objects.filter(owner=request.user)
        
        stats = {
            'total_folders': queryset.count(),
            'shared_folders': queryset.filter(is_shared=True).count(),
            'root_folders': queryset.filter(parent=None).count(),
            'colors_usage': {},
            'recent_folders': FolderListSerializer(
                queryset.order_by('-created_at')[:5], 
                many=True
            ).data
        }
        
        # Statistiques par couleur
        for choice in Folder.ColorChoices.choices:
            color_code, color_name = choice
            count = queryset.filter(color=color_code).count()
            if count > 0:
                stats['colors_usage'][color_name] = count
        
        return Response(stats)