# views.py
"""
Views pour la gestion des credentials avec sécurité et fonctionnalités avancées
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count, Case, When, IntegerField
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings
from django.core.cache import cache
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError, PermissionDenied as DRFPermissionDenied
import re
import secrets
import string
import hashlib
from datetime import timedelta, datetime
import logging
from collections import Counter
from .models import Category, Credential, PasswordHistory
from .serializers import (
    CategorySerializer,
    CredentialListSerializer,
    CredentialDetailSerializer,
    CredentialCreateSerializer,
    CredentialUpdateLastUsedSerializer,
    PasswordHistorySerializer
)

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Pagination personnalisée pour les credentials"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet pour les catégories"""
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'credential_count']
    ordering = ['name']
    
    def get_queryset(self):
        """Retourne toutes les catégories avec comptage des credentials de l'utilisateur"""
        return Category.objects.annotate(
            user_credential_count=Count(
                'credential',
                filter=Q(credential__owner=self.request.user)
            )
        ).distinct()
    
    @action(detail=True, methods=['get'])
    def credentials(self, request, pk=None):
        """Retourne les credentials d'une catégorie pour l'utilisateur connecté"""
        category = self.get_object()
        credentials = Credential.objects.filter(
            category=category,
            owner=request.user
        ).select_related('category', 'folder')
        
        serializer = CredentialListSerializer(credentials, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Statistiques des catégories pour l'utilisateur"""
        stats = Category.objects.annotate(
            user_credential_count=Count(
                'credential',
                filter=Q(credential__owner=request.user)
            )
        ).filter(user_credential_count__gt=0).values(
            'id', 'name', 'icon', 'color', 'user_credential_count'
        )
        
        return Response(list(stats))


class CredentialViewSet(viewsets.ModelViewSet):
    """ViewSet principal pour les credentials"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'username', 'url']
    ordering_fields = ['name', 'created_at', 'last_used_at', 'password_strength']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Retourne les credentials de l'utilisateur ou partagés avec lui"""
        base_queryset = Credential.objects.select_related(
            'category', 'folder', 'owner'
        ).prefetch_related('password_history')
        
        # Credentials possédés ou partagés
        user_credentials = Q(owner=self.request.user)
        shared_credentials = Q(is_shared=True)
        
        queryset = base_queryset.filter(user_credentials | shared_credentials)
        
        # Filtres additionnels
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        folder_id = self.request.query_params.get('folder')
        if folder_id:
            queryset = queryset.filter(folder_id=folder_id)
        
        is_favorite = self.request.query_params.get('is_favorite')
        if is_favorite == 'true':
            queryset = queryset.filter(is_favorite=True)
        
        weak_passwords = self.request.query_params.get('weak_passwords')
        if weak_passwords == 'true':
            queryset = queryset.filter(password_strength__lt=60)
        
        old_passwords = self.request.query_params.get('old_passwords')
        if old_passwords == 'true':
            threshold_date = timezone.now() - timedelta(days=90)
            queryset = queryset.filter(password_changed_at__lt=threshold_date)
        
        unused = self.request.query_params.get('unused')
        if unused == 'true':
            queryset = queryset.filter(last_used_at__isnull=True)
        
        return queryset.distinct()
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'list':
            return CredentialListSerializer
        elif self.action == 'create':
            return CredentialCreateSerializer
        elif self.action == 'mark_used':
            return CredentialUpdateLastUsedSerializer
        else:
            return CredentialDetailSerializer
    
    def perform_create(self, serializer):
        """Personnalise la création avec logs de sécurité"""
        credential = serializer.save()
        logger.info(f"Credential created: {credential.name} by {self.request.user.email}")
    
    def perform_update(self, serializer):
        """Personnalise la mise à jour avec vérifications de sécurité"""
        # Vérifier les permissions
        if serializer.instance.owner != self.request.user and not serializer.instance.is_shared:
            raise DRFPermissionDenied("Vous n'avez pas la permission de modifier ce credential")
        
        old_password = serializer.instance.decrypt_password()
        credential = serializer.save()
        
        # Si le mot de passe a changé, sauvegarder l'ancien dans l'historique
        if 'password' in serializer.validated_data:
            new_password = serializer.validated_data['password']
            if new_password and new_password != old_password:
                self._save_password_history(credential, old_password)
        
        logger.info(f"Credential updated: {credential.name} by {self.request.user.email}")
    
    def perform_destroy(self, instance):
        """Personnalise la suppression avec logs"""
        if instance.owner != self.request.user:
            raise DRFPermissionDenied("Vous n'avez pas la permission de supprimer ce credential")
        
        logger.info(f"Credential deleted: {instance.name} by {self.request.user.email}")
        super().perform_destroy(instance)
    
    def _save_password_history(self, credential, old_password):
        """Sauvegarde l'ancien mot de passe dans l'historique"""
        if old_password:
            # Hash du mot de passe pour l'historique (sécurisé)
            password_hash = hashlib.sha256(old_password.encode()).hexdigest()
            
            # Éviter les doublons
            if not PasswordHistory.objects.filter(
                credential=credential, 
                password_hash=password_hash
            ).exists():
                PasswordHistory.objects.create(
                    credential=credential,
                    password_hash=password_hash
                )
            
            # Limiter l'historique (garder seulement les 10 derniers)
            history_ids = PasswordHistory.objects.filter(
                credential=credential
            ).order_by('-created_at').values_list('id', flat=True)[10:]
            
            if history_ids:
                PasswordHistory.objects.filter(id__in=history_ids).delete()
    
    @action(detail=True, methods=['post'])
    def mark_used(self, request, pk=None):
        """Marque un credential comme utilisé récemment"""
        credential = self.get_object()
        
        # Vérifier les permissions
        if credential.owner != request.user and not credential.is_shared:
            raise DRFPermissionDenied("Accès refusé à ce credential")
        
        credential.update_last_used()
        logger.info(f"Credential marked as used: {credential.name} by {request.user.email}")
        
        serializer = self.get_serializer(credential)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        """Bascule le statut favori d'un credential"""
        credential = self.get_object()
        
        if credential.owner != request.user:
            raise DRFPermissionDenied("Vous ne pouvez modifier que vos propres credentials")
        
        credential.is_favorite = not credential.is_favorite
        credential.save(update_fields=['is_favorite'])
        
        serializer = CredentialDetailSerializer(credential, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def password_strength(self, request, pk=None):
        """Analyse la force du mot de passe"""
        credential = self.get_object()
        
        if credential.owner != request.user and not credential.is_shared:
            raise DRFPermissionDenied("Accès refusé à ce credential")
        
        password = credential.decrypt_password()
        analysis = self._analyze_password_strength(password)
        
        return Response(analysis)
    
    def _analyze_password_strength(self, password):
        """Analyse détaillée de la force d'un mot de passe"""
        if not password:
            return {
                'score': 0,
                'level': 'Aucun',
                'recommendations': ['Définir un mot de passe']
            }
        
        analysis = {
            'length': len(password),
            'has_lowercase': bool(re.search(r'[a-z]', password)),
            'has_uppercase': bool(re.search(r'[A-Z]', password)),
            'has_digits': bool(re.search(r'\d', password)),
            'has_symbols': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
            'has_common_patterns': self._check_common_patterns(password),
        }
        
        # Calcul du score
        score = 0
        recommendations = []
        
        # Longueur
        if analysis['length'] >= 8:
            score += 20
        else:
            recommendations.append('Utiliser au moins 8 caractères')
            
        if analysis['length'] >= 12:
            score += 10
        elif analysis['length'] < 12:
            recommendations.append('Utiliser au moins 12 caractères pour plus de sécurité')
            
        if analysis['length'] >= 16:
            score += 10
        
        # Types de caractères
        if analysis['has_lowercase']:
            score += 10
        else:
            recommendations.append('Ajouter des lettres minuscules')
            
        if analysis['has_uppercase']:
            score += 10
        else:
            recommendations.append('Ajouter des lettres majuscules')
            
        if analysis['has_digits']:
            score += 15
        else:
            recommendations.append('Ajouter des chiffres')
            
        if analysis['has_symbols']:
            score += 25
        else:
            recommendations.append('Ajouter des caractères spéciaux')
        
        # Pénalités
        if analysis['has_common_patterns']:
            score -= 20
            recommendations.append('Éviter les motifs courants (123, abc, qwerty)')
        
        # Niveau
        if score >= 80:
            level = 'Très fort'
        elif score >= 60:
            level = 'Fort'
        elif score >= 40:
            level = 'Moyen'
        elif score >= 20:
            level = 'Faible'
        else:
            level = 'Très faible'
        
        return {
            'score': max(0, min(100, score)),
            'level': level,
            'analysis': analysis,
            'recommendations': recommendations
        }
    
    def _check_common_patterns(self, password):
        """Vérifie la présence de motifs courants"""
        import re
        common_patterns = [
            r'123', r'abc', r'qwerty', r'azerty', r'password',
            r'admin', r'user', r'login', r'welcome'
        ]
        
        password_lower = password.lower()
        return any(re.search(pattern, password_lower) for pattern in common_patterns)
    
    @action(detail=False, methods=['post'])
    def generate_password(self, request):
        """Génère un mot de passe sécurisé"""
        length = int(request.data.get('length', 16))
        include_symbols = request.data.get('include_symbols', True)
        include_numbers = request.data.get('include_numbers', True)
        include_uppercase = request.data.get('include_uppercase', True)
        include_lowercase = request.data.get('include_lowercase', True)
        exclude_ambiguous = request.data.get('exclude_ambiguous', False)
        
        # Validation
        if length < 4 or length > 128:
            raise ValidationError("La longueur doit être entre 4 et 128 caractères")
        
        password = self._generate_secure_password(
            length, include_symbols, include_numbers, 
            include_uppercase, include_lowercase, exclude_ambiguous
        )
        
        analysis = self._analyze_password_strength(password)
        
        return Response({
            'password': password,
            'strength': analysis
        })
    
    def _generate_secure_password(self, length, include_symbols=True, include_numbers=True, 
                                 include_uppercase=True, include_lowercase=True, exclude_ambiguous=False):
        """Génère un mot de passe sécurisé avec les options spécifiées"""
        characters = ""
        required_chars = []
        
        if include_lowercase:
            chars = string.ascii_lowercase
            if exclude_ambiguous:
                chars = chars.replace('l', '').replace('o', '')
            characters += chars
            required_chars.append(secrets.choice(chars))
        
        if include_uppercase:
            chars = string.ascii_uppercase
            if exclude_ambiguous:
                chars = chars.replace('I', '').replace('O', '')
            characters += chars
            required_chars.append(secrets.choice(chars))
        
        if include_numbers:
            chars = string.digits
            if exclude_ambiguous:
                chars = chars.replace('0', '').replace('1', '')
            characters += chars
            required_chars.append(secrets.choice(chars))
        
        if include_symbols:
            chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            characters += chars
            required_chars.append(secrets.choice(chars))
        
        if not characters:
            raise ValidationError("Au moins un type de caractère doit être sélectionné")
        
        # Générer le reste du mot de passe
        remaining_length = max(0, length - len(required_chars))
        random_chars = [secrets.choice(characters) for _ in range(remaining_length)]
        
        # Mélanger tous les caractères
        all_chars = required_chars + random_chars
        secrets.SystemRandom().shuffle(all_chars)
        
        return ''.join(all_chars)
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Statistiques pour le tableau de bord"""
        user_credentials = Credential.objects.filter(owner=request.user)
        
        total_count = user_credentials.count()
        
        # Statistiques de sécurité
        weak_passwords = user_credentials.filter(password_strength__lt=60).count()
        old_passwords = user_credentials.filter(
            password_changed_at__lt=timezone.now() - timedelta(days=90)
        ).count()
        unused_credentials = user_credentials.filter(last_used_at__isnull=True).count()
        favorites_count = user_credentials.filter(is_favorite=True).count()
        
        # Répartition par catégorie
        categories_stats = user_credentials.values(
            'category__name', 'category__icon', 'category__color'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Activité récente (derniers 30 jours)
        recent_activity = user_credentials.filter(
            last_used_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        return Response({
            'total_credentials': total_count,
            'weak_passwords': weak_passwords,
            'old_passwords': old_passwords,
            'unused_credentials': unused_credentials,
            'favorites': favorites_count,
            'recent_activity': recent_activity,
            'categories_distribution': list(categories_stats),
            'security_score': self._calculate_security_score(
                total_count, weak_passwords, old_passwords, unused_credentials
            )
        })
    
    def _calculate_security_score(self, total, weak, old, unused):
        """Calcule un score de sécurité global"""
        if total == 0:
            return 100
        
        weak_ratio = weak / total
        old_ratio = old / total
        unused_ratio = unused / total
        
        # Score basé sur les ratios (100 = parfait, 0 = très mauvais)
        score = 100
        score -= (weak_ratio * 40)  # -40 points max pour mots de passe faibles
        score -= (old_ratio * 30)   # -30 points max pour mots de passe anciens
        score -= (unused_ratio * 20) # -20 points max pour credentials inutilisés
        
        return max(0, min(100, int(score)))
    
    @action(detail=False, methods=['get'])
    def export_data(self, request):
        """Exporte les données utilisateur (sans mots de passe)"""
        credentials = Credential.objects.filter(owner=request.user).select_related('category')
        
        export_data = []
        for credential in credentials:
            export_data.append({
                'name': credential.name,
                'username': credential.username,
                'url': credential.url,
                'category': credential.category.name if credential.category else None,
                'notes': credential.decrypt_notes(),
                'created_at': credential.created_at.isoformat(),
                'last_used_at': credential.last_used_at.isoformat() if credential.last_used_at else None,
            })
        
        logger.info(f"Data exported by {request.user.email}")
        
        return Response({
            'export_date': timezone.now().isoformat(),
            'total_credentials': len(export_data),
            'credentials': export_data
        })

    # action pour renvoyer le mot de passe du credential en clair
    @action(detail=True, methods=['get'])
    def reveal_password(self, request, pk=None):
        """Retourne le mot de passe en clair d'un credential"""
        credential = self.get_object()
        print(credential.decrypt_password())
        
        if credential.owner != request.user and not credential.is_shared:
            raise DRFPermissionDenied("Accès refusé à ce credential")
        
        password = credential.decrypt_password()
        
        if not password:
            return Response({'error': 'Aucun mot de passe défini'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({'password': password})

    @action(detail=False, methods=['post'], url_path='analyze-password')
    def analyze_password(self, request):
        """
        Analyse la force d'un mot de passe sans le stocker
        """
        password = request.data.get('password')

        if not password:
            return Response(
                {'error': 'Le mot de passe est requis'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Créer un hash pour la mise en cache (sans exposer le mot de passe)
        password_hash = hashlib.sha256(password.encode()).hexdigest()[:16]
        cache_key = f'password_analysis_{password_hash}'

        # Vérifier le cache
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result)

        analysis = self._analyze_password_strength(password)

        # Mettre en cache pour 1 heure
        cache.set(cache_key, analysis, 3600)

        return Response(analysis)

    def _analyze_password_strength(self, password):
        """
        Analyse complète de la force d'un mot de passe
        """
        if not password:
            return {
                'score': 0,
                'level': 'Aucun',
                'analysis': {
                    'length': 0,
                    'has_lowercase': False,
                    'has_uppercase': False,
                    'has_digits': False,
                    'has_symbols': False,
                    'has_common_patterns': False,
                    'entropy': 0,
                    'uniqueness': 0,
                    'dictionary_words': [],
                },
                'recommendations': ['Définir un mot de passe']
            }

        # Analyse de base
        analysis = {
            'length': len(password),
            'has_lowercase': bool(re.search(r'[a-z]', password)),
            'has_uppercase': bool(re.search(r'[A-Z]', password)),
            'has_digits': bool(re.search(r'\d', password)),
            'has_symbols': bool(re.search(r'[!@#$%^&*(),.?":{}|<>[\]\\/_+=~`\-;\'§]', password)),
            'has_common_patterns': self._check_common_patterns(password),
            'entropy': self._calculate_entropy(password),
            'uniqueness': self._calculate_uniqueness(password),
            'dictionary_words': self._check_dictionary_words(password),
            'repeated_chars': self._check_repeated_chars(password),
            'sequential_chars': self._check_sequential_chars(password),
            'keyboard_patterns': self._check_keyboard_patterns(password),
        }

        # Calcul du score
        score = 0
        recommendations = []

        # Points pour la longueur
        length = analysis['length']
        if length >= 8:
            score += 15
        else:
            recommendations.append(f'Utiliser au moins 8 caractères (actuellement {length})')

        if length >= 12:
            score += 10
        elif length >= 8:
            recommendations.append('Utiliser au moins 12 caractères pour une sécurité optimale')

        if length >= 16:
            score += 10
        elif length >= 12:
            recommendations.append('Utiliser 16+ caractères pour une sécurité maximale')

        # Points pour les types de caractères
        character_types = 0
        if analysis['has_lowercase']:
            score += 5
            character_types += 1
        else:
            recommendations.append('Ajouter des lettres minuscules')

        if analysis['has_uppercase']:
            score += 5
            character_types += 1
        else:
            recommendations.append('Ajouter des lettres majuscules')

        if analysis['has_digits']:
            score += 10
            character_types += 1
        else:
            recommendations.append('Ajouter des chiffres')

        if analysis['has_symbols']:
            score += 15
            character_types += 1
        else:
            recommendations.append('Ajouter des caractères spéciaux (!@#$...)')

        # Bonus pour la diversité des caractères
        if character_types >= 3:
            score += 10
        if character_types == 4:
            score += 5

        # Points pour l'entropie
        if analysis['entropy'] >= 4.0:
            score += 15
        elif analysis['entropy'] >= 3.5:
            score += 10
        elif analysis['entropy'] >= 3.0:
            score += 5
        else:
            recommendations.append('Utiliser une plus grande variété de caractères')

        # Points pour l'unicité
        if analysis['uniqueness'] >= 0.8:
            score += 10
        elif analysis['uniqueness'] >= 0.6:
            score += 5
        else:
            recommendations.append('Éviter les caractères répétés')

        # Pénalités
        penalties = 0

        if analysis['has_common_patterns']:
            penalties += 25
            recommendations.append('Éviter les motifs courants (123, abc, qwerty, etc.)')

        if analysis['dictionary_words']:
            penalties += 15
            recommendations.append(f'Éviter les mots du dictionnaire: {", ".join(analysis["dictionary_words"][:3])}')

        if analysis['repeated_chars'] > 2:
            penalties += 10
            recommendations.append('Réduire les caractères répétés consécutifs')

        if analysis['sequential_chars']:
            penalties += 15
            recommendations.append('Éviter les séquences de caractères (abc, 123, etc.)')

        if analysis['keyboard_patterns']:
            penalties += 20
            recommendations.append('Éviter les motifs du clavier (qwerty, azerty, etc.)')

        # Score final
        final_score = max(0, min(100, score - penalties))

        # Niveau de sécurité
        if final_score >= 90:
            level = 'Excellent'
            color = '#22c55e'  # green-500
        elif final_score >= 80:
            level = 'Très fort'
            color = '#16a34a'  # green-600
        elif final_score >= 70:
            level = 'Fort'
            color = '#65a30d'  # lime-600
        elif final_score >= 60:
            level = 'Moyen'
            color = '#eab308'  # yellow-500
        elif final_score >= 40:
            level = 'Faible'
            color = '#f97316'  # orange-500
        elif final_score >= 20:
            level = 'Très faible'
            color = '#ef4444'  # red-500
        else:
            level = 'Critique'
            color = '#dc2626'  # red-600

        # Estimations de temps de craquage
        crack_time = self._estimate_crack_time(password, final_score)

        return {
            'score': final_score,
            'level': level,
            'color': color,
            'analysis': analysis,
            'recommendations': recommendations[:5],  # Limiter à 5 recommandations
            'crack_time': crack_time,
            'details': {
                'character_types': character_types,
                'base_score': score,
                'penalties': penalties,
                'entropy_bits': round(analysis['entropy'] * len(password), 1) if analysis['entropy'] else 0,
            }
        }

    def _check_common_patterns(self, password):
        """Vérifie les motifs courants dangereux"""
        password_lower = password.lower()

        common_patterns = [
            # Séquences numériques
            r'123+', r'234+', r'345+', r'456+', r'567+', r'678+', r'789+',
            r'987+', r'876+', r'765+', r'654+', r'543+', r'432+', r'321+',

            # Séquences alphabétiques  
            r'abc+', r'bcd+', r'cde+', r'def+', r'efg+', r'fgh+',
            r'zyx+', r'yxw+', r'xwv+', r'wvu+', r'vut+', r'uts+',

            # Motifs de clavier
            r'qwer+', r'asdf+', r'zxcv+', r'qwerty+', r'azerty+',
            r'uiop+', r'hjkl+', r'nm,+', r'./;+',

            # Mots courants
            r'password+', r'motdepasse+', r'admin+', r'user+', r'login+',
            r'welcome+', r'bonjour+', r'salut+', r'test+', r'demo+',

            # Dates courantes
            r'202[0-9]', r'199[0-9]', r'198[0-9]',

            # Répétitions
            r'(.)\1{2,}',  # 3+ caractères identiques consécutifs
        ]

        return any(re.search(pattern, password_lower) for pattern in common_patterns)

    def _calculate_entropy(self, password):
        """Calcule l'entropie du mot de passe"""
        if not password:
            return 0

        # Compter la fréquence de chaque caractère
        char_counts = Counter(password)
        password_length = len(password)

        # Calculer l'entropie de Shannon
        entropy = 0
        import math
        for count in char_counts.values():
            probability = count / password_length
            if probability > 0:
                entropy -= probability * math.log2(probability)

        return entropy

    def _calculate_uniqueness(self, password):
        """Calcule le ratio de caractères uniques"""
        if not password:
            return 0

        unique_chars = len(set(password))
        total_chars = len(password)

        return unique_chars / total_chars

    def _check_dictionary_words(self, password):
        """Vérifie la présence de mots du dictionnaire courants"""
        password_lower = password.lower()

        # Liste de mots courants français et anglais
        common_words = [
            'password', 'motdepasse', 'admin', 'user', 'login', 'welcome',
            'bonjour', 'salut', 'hello', 'world', 'test', 'demo', 'azerty',
            'qwerty', 'secret', 'passe', 'code', 'clef', 'key', 'open',
            'ouvrir', 'fermer', 'close', 'start', 'stop', 'begin', 'end',
            'premier', 'dernier', 'first', 'last', 'nouveau', 'new', 'old',
            'ancien', 'facile', 'easy', 'simple', 'basic', 'master', 'maitre'
        ]

        found_words = []
        for word in common_words:
            if len(word) >= 4 and word in password_lower:
                found_words.append(word)

        return found_words

    def _check_repeated_chars(self, password):
        """Compte les caractères répétés consécutifs"""
        if not password:
            return 0

        max_repeat = 1
        current_repeat = 1

        for i in range(1, len(password)):
            if password[i] == password[i-1]:
                current_repeat += 1
                max_repeat = max(max_repeat, current_repeat)
            else:
                current_repeat = 1

        return max_repeat

    def _check_sequential_chars(self, password):
        """Vérifie les séquences de caractères"""
        if len(password) < 3:
            return False

        for i in range(len(password) - 2):
            # Vérifier séquence croissante
            if (ord(password[i+1]) == ord(password[i]) + 1 and 
                ord(password[i+2]) == ord(password[i]) + 2):
                return True

            # Vérifier séquence décroissante  
            if (ord(password[i+1]) == ord(password[i]) - 1 and 
                ord(password[i+2]) == ord(password[i]) - 2):
                return True

        return False

    def _check_keyboard_patterns(self, password):
        """Vérifie les motifs de clavier"""
        password_lower = password.lower()

        keyboard_rows = [
            'qwertyuiop',
            'asdfghjkl', 
            'zxcvbnm',
            'azertyuiop',
            'qsdfghjklm',
            'wxcvbn'
        ]

        for row in keyboard_rows:
            for i in range(len(row) - 2):
                pattern = row[i:i+3]
                if pattern in password_lower or pattern[::-1] in password_lower:
                    return True

        return False

    def _estimate_crack_time(self, password, score):
        """Estime le temps de craquage approximatif"""
        if not password:
            return {'online': 'Instantané', 'offline': 'Instantané'}

        # Calculer l'espace de clés approximatif
        charset_size = 0
        if re.search(r'[a-z]', password):
            charset_size += 26
        if re.search(r'[A-Z]', password):
            charset_size += 26  
        if re.search(r'\d', password):
            charset_size += 10
        if re.search(r'[!@#$%^&*(),.?":{}|<>[\]\\/_+=~`\-;\'§]', password):
            charset_size += 32

        if charset_size == 0:
            return {'online': 'Instantané', 'offline': 'Instantané'}

        # Nombre de combinaisons possibles
        combinations = charset_size ** len(password)

        # Temps moyens (la moitié de l'espace)
        avg_combinations = combinations / 2

        # Vitesses approximatives (tentatives par seconde)
        online_speed = 1000  # Attaque en ligne avec limitations
        offline_speed = 1e9  # Attaque hors ligne avec GPU

        # Calculer les temps
        online_seconds = avg_combinations / online_speed
        offline_seconds = avg_combinations / offline_speed

        def format_time(seconds):
            if seconds < 1:
                return "Instantané"
            elif seconds < 60:
                return f"{int(seconds)} secondes"
            elif seconds < 3600:
                return f"{int(seconds/60)} minutes"
            elif seconds < 86400:
                return f"{int(seconds/3600)} heures"
            elif seconds < 31536000:
                return f"{int(seconds/86400)} jours"
            else:
                return f"{int(seconds/31536000)} années"

        return {
            'online': format_time(online_seconds),
            'offline': format_time(offline_seconds),
            'combinations': int(combinations) if combinations < 1e15 else f"{combinations:.2e}"
        }


@method_decorator(cache_page(60 * 15), name='dispatch')  # Cache 15 minutes
class PasswordHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour l'historique des mots de passe (lecture seule)"""
    serializer_class = PasswordHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        credential_id = self.kwargs.get('pk')
        if credential_id:
            credential = get_object_or_404(Credential, id=credential_id)
            
            # Vérifier les permissions
            if credential.owner != self.request.user and not credential.is_shared:
                raise DRFPermissionDenied("Accès refusé à cet historique")
            
            return PasswordHistory.objects.filter(credential=credential).order_by('-created_at')
        
        return PasswordHistory.objects.none()


# Views utilitaires pour des actions spécifiques
@login_required
def check_password_breach(request, credential_id):
    """Vérifie si un mot de passe a été compromis (API externe)"""
    try:
        credential = get_object_or_404(Credential, id=credential_id, owner=request.user)
        password = credential.decrypt_password()
        
        if not password:
            return JsonResponse({'is_breached': False, 'message': 'Aucun mot de passe'})
        
        # Ici vous pouvez intégrer une API comme HaveIBeenPwned
        # Pour cet exemple, on simule la vérification
        import hashlib
        password_hash = hashlib.sha1(password.encode()).hexdigest().upper()
        
        # Simulation - en réalité, vous appelleriez l'API HaveIBeenPwned
        is_breached = False  # Remplacer par l'appel réel à l'API
        
        return JsonResponse({
            'is_breached': is_breached,
            'message': 'Mot de passe compromis' if is_breached else 'Mot de passe sécurisé'
        })
        
    except Exception as e:
        logger.error(f"Error checking password breach: {e}")
        return JsonResponse({'error': 'Erreur lors de la vérification'}, status=500)


