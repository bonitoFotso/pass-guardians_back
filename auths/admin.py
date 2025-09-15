from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Administration des utilisateurs personnalisés"""
    
    # Champs affichés dans la liste
    list_display = (
        'email', 
        'username', 
        'first_name', 
        'last_name', 
        'is_active', 
        'is_staff', 
        'is_superuser',
        'date_joined',
    )
    
    # Champs pour filtrer
    list_filter = (
        'is_active', 
        'is_staff', 
        'is_superuser', 
        'date_joined',
        'last_login'
    )
    
    # Champs de recherche
    search_fields = ('email', 'username', 'first_name', 'last_name')
    
    # Organisation des champs dans le formulaire d'édition
    fieldsets = (
        (None, {
            'fields': ('email', 'username', 'password')
        }),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name')
        }),
        (_('Permissions'), {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            ),
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')
        }),
    )
    
    # Champs en lecture seule
    readonly_fields = ('date_joined', 'last_login', 'created_at', 'updated_at')
    
    # Champs pour le formulaire d'ajout
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 
                'username', 
                'first_name', 
                'last_name', 
                'password1', 
                'password2'
            ),
        }),
        (_('Permissions'), {
            'fields': ('is_staff', 'is_active')
        }),
    )
    
    # Ordre par défaut
    ordering = ('email',)
    
    def has_technicien_profile(self, obj):
        """Vérifie si l'utilisateur a un profil technicien"""
        return hasattr(obj, 'technicien_profile')
    has_technicien_profile.short_description = 'Profil Technicien'
    has_technicien_profile.boolean = True








# Personnalisation du titre et de l'en-tête de l'admin
admin.site.site_header = "Administration du Système"
admin.site.site_title = "Admin"
admin.site.index_title = "Panneau d'administration"