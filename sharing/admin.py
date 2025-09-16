# admin.py
"""
Configuration de l'administration Django pour les modèles de partage
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import SharedCredential, SharedFolder


@admin.register(SharedCredential)
class SharedCredentialAdmin(admin.ModelAdmin):
    list_display = [
        'credential_name', 
        'shared_with_user', 
        'permission', 
        'shared_by', 
        'shared_at', 
        'expires_at', 
        'status_display',
        'is_expired_display'
    ]
    
    list_filter = [
        'permission',
        'is_active',
        'shared_at',
        'expires_at',
        ('expires_at', admin.DateFieldListFilter),
    ]
    
    search_fields = [
        'credential__name',
        'user__email',
        'user__username',
        'shared_by__email',
        'shared_by__username'
    ]
    
    date_hierarchy = 'shared_at'
    
    readonly_fields = [
        'shared_at',
        'is_expired_display',
        'permissions_info'
    ]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('credential', 'user', 'shared_by')
        }),
        ('Permissions', {
            'fields': ('permission', 'permissions_info'),
            'description': 'Permissions accordées à l\'utilisateur'
        }),
        ('Statut et dates', {
            'fields': ('is_active', 'shared_at', 'expires_at', 'is_expired_display')
        }),
    )
    
    raw_id_fields = ['credential', 'user', 'shared_by']
    
    def credential_name(self, obj):
        """Affiche le nom du credential avec lien"""
        if obj.credential:
            # Utilisez le bon nom d'app et de modèle selon votre structure
            # Format: admin:app_model_change
            try:
                url = reverse('admin:core_credential_change', args=[obj.credential.pk])
                return format_html('<a href="{}">{}</a>', url, obj.credential.name)
            except:
                # Si le reverse échoue, afficher juste le nom sans lien
                return obj.credential.name
        return '-'
    credential_name.short_description = 'Credential'
    credential_name.admin_order_field = 'credential__name'
    
    def shared_with_user(self, obj):
        """Affiche l'utilisateur avec qui c'est partagé"""
        if obj.user:
            url = reverse('admin:auths_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email or obj.user.username)
        return '-'
    shared_with_user.short_description = 'Partagé avec'
    shared_with_user.admin_order_field = 'user__email'
    
    def status_display(self, obj):
        """Affiche le statut avec couleur"""
        if not obj.is_active:
            return format_html('<span style="color: red;">Inactif</span>')
        elif obj.is_expired:
            return format_html('<span style="color: orange;">Expiré</span>')
        else:
            return format_html('<span style="color: green;">Actif</span>')
    status_display.short_description = 'Statut'
    
    def is_expired_display(self, obj):
        """Affiche si le partage a expiré"""
        if obj.expires_at:
            if obj.is_expired:
                return format_html('<span style="color: red;">Oui</span>')
            else:
                return format_html('<span style="color: green;">Non</span>')
        return 'Jamais'
    is_expired_display.short_description = 'Expiré'
    
    def permissions_info(self, obj):
        """Affiche les informations sur les permissions"""
        permissions = {
            'read': 'Lecture seule',
            'write': 'Lecture et écriture',
            'share': 'Lecture, écriture et partage',
            'admin': 'Administration complète'
        }
        current_perm = permissions.get(obj.permission, obj.permission)
        
        info = f"<strong>Permission actuelle:</strong> {current_perm}<br>"
        info += "<strong>Peut faire:</strong><ul>"
        
        if obj.has_permission('read'):
            info += "<li>Lire le credential</li>"
        if obj.has_permission('write'):
            info += "<li>Modifier le credential</li>"
        if obj.has_permission('share'):
            info += "<li>Partager le credential</li>"
        if obj.has_permission('admin'):
            info += "<li>Administration complète</li>"
            
        info += "</ul>"
        return mark_safe(info)
    permissions_info.short_description = 'Détails des permissions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'credential', 'user', 'shared_by'
        )


@admin.register(SharedFolder)
class SharedFolderAdmin(admin.ModelAdmin):
    list_display = [
        'folder_name',
        'shared_with_user',
        'permission',
        'shared_by',
        'shared_at',
        'expires_at',
        'status_display',
        'is_expired_display'
    ]
    
    list_filter = [
        'permission',
        'is_active',
        'shared_at',
        'expires_at',
        ('expires_at', admin.DateFieldListFilter),
    ]
    
    search_fields = [
        'folder__name',
        'user__email',
        'user__username',
        'shared_by__email',
        'shared_by__username'
    ]
    
    date_hierarchy = 'shared_at'
    
    readonly_fields = [
        'shared_at',
        'is_expired_display',
        'permissions_info'
    ]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('folder', 'user', 'shared_by')
        }),
        ('Permissions', {
            'fields': ('permission', 'permissions_info'),
            'description': 'Permissions accordées à l\'utilisateur'
        }),
        ('Statut et dates', {
            'fields': ('is_active', 'shared_at', 'expires_at', 'is_expired_display')
        }),
    )
    
    raw_id_fields = ['folder', 'user', 'shared_by']
    
    def folder_name(self, obj):
        """Affiche le nom du dossier avec lien"""
        if obj.folder:
            try:
                url = reverse('admin:core_folder_change', args=[obj.folder.pk])
                return format_html('<a href="{}">{}</a>', url, obj.folder.name)
            except:
                # Si le reverse échoue, afficher juste le nom sans lien
                return obj.folder.name
        return '-'
    folder_name.short_description = 'Dossier'
    folder_name.admin_order_field = 'folder__name'
    
    def shared_with_user(self, obj):
        """Affiche l'utilisateur avec qui c'est partagé"""
        if obj.user:
            url = reverse('admin:auths_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email or obj.user.username)
        return '-'
    shared_with_user.short_description = 'Partagé avec'
    shared_with_user.admin_order_field = 'user__email'
    
    def status_display(self, obj):
        """Affiche le statut avec couleur"""
        if not obj.is_active:
            return format_html('<span style="color: red;">Inactif</span>')
        elif obj.is_expired:
            return format_html('<span style="color: orange;">Expiré</span>')
        else:
            return format_html('<span style="color: green;">Actif</span>')
    status_display.short_description = 'Statut'
    
    def is_expired_display(self, obj):
        """Affiche si le partage a expiré"""
        if obj.expires_at:
            if obj.is_expired:
                return format_html('<span style="color: red;">Oui</span>')
            else:
                return format_html('<span style="color: green;">Non</span>')
        return 'Jamais'
    is_expired_display.short_description = 'Expiré'
    
    def permissions_info(self, obj):
        """Affiche les informations sur les permissions"""
        permissions = {
            'read': 'Lecture seule',
            'write': 'Lecture et écriture', 
            'share': 'Lecture, écriture et partage',
            'admin': 'Administration complète'
        }
        current_perm = permissions.get(obj.permission, obj.permission)
        
        info = f"<strong>Permission actuelle:</strong> {current_perm}<br>"
        info += "<strong>Peut faire:</strong><ul>"
        
        if obj.has_permission('read'):
            info += "<li>Lire le dossier</li>"
        if obj.has_permission('write'):
            info += "<li>Modifier le dossier</li>"
        if obj.has_permission('share'):
            info += "<li>Partager le dossier</li>"
        if obj.has_permission('admin'):
            info += "<li>Administration complète</li>"
            
        info += "</ul>"
        return mark_safe(info)
    permissions_info.short_description = 'Détails des permissions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'folder', 'user', 'shared_by'
        )


# Actions personnalisées
def activate_sharing(modeladmin, request, queryset):
    """Active les partages sélectionnés"""
    updated = queryset.update(is_active=True)
    modeladmin.message_user(
        request, 
        f"{updated} partage(s) activé(s) avec succès."
    )
activate_sharing.short_description = "Activer les partages sélectionnés"

def deactivate_sharing(modeladmin, request, queryset):
    """Désactive les partages sélectionnés"""
    updated = queryset.update(is_active=False)
    modeladmin.message_user(
        request,
        f"{updated} partage(s) désactivé(s) avec succès."
    )
deactivate_sharing.short_description = "Désactiver les partages sélectionnés"

def extend_expiration(modeladmin, request, queryset):
    """Étend l'expiration d'un mois"""
    from datetime import timedelta
    for obj in queryset:
        if obj.expires_at:
            obj.expires_at += timedelta(days=30)
            obj.save()
    modeladmin.message_user(
        request,
        f"Expiration étendue de 30 jours pour {queryset.count()} partage(s)."
    )
extend_expiration.short_description = "Étendre l'expiration de 30 jours"

# Ajout des actions aux classes admin
SharedCredentialAdmin.actions = [activate_sharing, deactivate_sharing, extend_expiration]
SharedFolderAdmin.actions = [activate_sharing, deactivate_sharing, extend_expiration]