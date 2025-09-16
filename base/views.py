from rest_framework import generics, status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import AppSettings
from .serializers import (
    AppSettingsSerializer,
    AppSettingsUpdateSerializer,
    AppSettingsChoicesSerializer,
    AppSettingsCreateSerializer
)

User = get_user_model()


class AppSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet complet pour la gestion des paramètres d'application
    Permet CRUD + actions personnalisées
    """
    
    serializer_class = AppSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """L'utilisateur ne voit que ses propres paramètres"""
        return AppSettings.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Choix du serializer selon l'action"""
        if self.action == 'create':
            return AppSettingsCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AppSettingsUpdateSerializer
        return AppSettingsSerializer
    
    def perform_create(self, serializer):
        """Création avec l'utilisateur courant"""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def choices(self, request):
        """Retourne les choix disponibles pour les champs"""
        serializer = AppSettingsChoicesSerializer({})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reset_to_default(self, request, pk=None):
        """Réinitialise les paramètres aux valeurs par défaut"""
        settings = self.get_object()
        
        with transaction.atomic():
            settings.theme = AppSettings.ThemeChoices.SYSTEM
            settings.auto_lock_timeout = AppSettings.TimeoutChoices.THIRTY_MIN
            settings.clipboard_clear_timeout = AppSettings.ClipboardTimeoutChoices.THIRTY_SEC
            settings.enable_biometric = False
            settings.show_password_strength = True
            settings.auto_fill_enabled = True
            settings.breach_monitoring = True
            settings.login_notifications = True
            settings.export_format = AppSettings.ExportFormatChoices.CSV
            settings.save()
        
        serializer = self.get_serializer(settings)
        return Response(
            {
                'message': 'Paramètres réinitialisés aux valeurs par défaut',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def my_settings(self, request):
        """Récupère les paramètres de l'utilisateur courant"""
        settings, created = AppSettings.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(settings)
        
        response_data = serializer.data
        if created:
            response_data['message'] = 'Paramètres créés avec les valeurs par défaut'
        
        return Response(response_data)


class AppSettingsListCreateView(generics.ListCreateAPIView):
    """Vue pour lister et créer les paramètres (alternative au ViewSet)"""
    
    serializer_class = AppSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return AppSettings.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AppSettingsCreateSerializer
        return AppSettingsSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AppSettingsRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Vue pour récupérer, modifier et supprimer les paramètres"""
    
    serializer_class = AppSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return AppSettings.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AppSettingsUpdateSerializer
        return AppSettingsSerializer


class UserSettingsView(APIView):
    """Vue spécialisée pour les paramètres de l'utilisateur courant"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Récupère ou crée les paramètres de l'utilisateur"""
        settings, created = AppSettings.objects.get_or_create(user=request.user)
        serializer = AppSettingsSerializer(settings)
        
        response_data = {
            'settings': serializer.data,
            'is_new': created
        }
        
        return Response(response_data)
    
    def put(self, request):
        """Mise à jour complète des paramètres"""
        settings, created = AppSettings.objects.get_or_create(user=request.user)
        serializer = AppSettingsUpdateSerializer(settings, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """Mise à jour partielle des paramètres"""
        settings, created = AppSettings.objects.get_or_create(user=request.user)
        serializer = AppSettingsUpdateSerializer(
            settings, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        """Supprime les paramètres (réinitialisation)"""
        try:
            settings = AppSettings.objects.get(user=request.user)
            settings.delete()
            return Response(
                {'message': 'Paramètres supprimés'}, 
                status=status.HTTP_204_NO_CONTENT
            )
        except AppSettings.DoesNotExist:
            return Response(
                {'message': 'Aucun paramètre à supprimer'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class AppSettingsChoicesView(APIView):
    """Vue pour récupérer les choix disponibles"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Retourne tous les choix disponibles"""
        serializer = AppSettingsChoicesSerializer({})
        return Response(serializer.data)


class AppSettingsBulkUpdateView(APIView):
    """Vue pour la mise à jour en lot de plusieurs paramètres"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def patch(self, request):
        """Mise à jour de plusieurs paramètres à la fois"""
        settings, created = AppSettings.objects.get_or_create(user=request.user)
        
        # Dictionnaire des champs modifiables
        allowed_fields = [
            'theme', 'auto_lock_timeout', 'clipboard_clear_timeout',
            'enable_biometric', 'show_password_strength', 'auto_fill_enabled',
            'breach_monitoring', 'login_notifications', 'export_format'
        ]
        
        # Filtrer seulement les champs autorisés
        filtered_data = {
            key: value for key, value in request.data.items() 
            if key in allowed_fields
        }
        
        if not filtered_data:
            return Response(
                {'message': 'Aucun champ valide à mettre à jour'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = AppSettingsUpdateSerializer(
            settings, 
            data=filtered_data, 
            partial=True
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
            
            # Retourner les paramètres complets
            full_serializer = AppSettingsSerializer(settings)
            return Response({
                'message': f'{len(filtered_data)} paramètre(s) mis à jour',
                'updated_fields': list(filtered_data.keys()),
                'settings': full_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AppSettingsExportView(APIView):
    """Vue pour exporter les paramètres de l'utilisateur"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Exporte les paramètres au format demandé"""
        try:
            settings = AppSettings.objects.get(user=request.user)
        except AppSettings.DoesNotExist:
            return Response(
                {'message': 'Aucun paramètre trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AppSettingsSerializer(settings)
        export_data = {
            'user': request.user.email,
            'export_date': timezone.now().isoformat(),
            'settings': serializer.data
        }
        
        return Response(export_data)