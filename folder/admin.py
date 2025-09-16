# admin.py
"""
Administration pour les dossiers
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Folder


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    """Administration des dossiers"""
    
    list_display = ['name', 'colored_name', 'owner', 'parent', 'full_path_display', 'is_shared', 'created_at']
    list_filter = ['color', 'is_shared', 'created_at', 'owner']
    search_fields = ['name', 'owner__email', 'owner__username']
    list_select_related = ['owner', 'parent']
    readonly_fields = ['created_at', 'updated_at', 'full_path_display']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'parent', 'owner')
        }),
        ('Apparence', {
            'fields': ('color', 'is_shared')
        }),
        ('Métadonnées', {
            'fields': ('full_path_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def colored_name(self, obj):
        """Affiche le nom avec la couleur associée"""
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            obj.color,
            obj.name
        )
    colored_name.short_description = 'Nom (coloré)'
    
    def full_path_display(self, obj):
        """Affiche le chemin complet du dossier"""
        return obj.full_path
    full_path_display.short_description = 'Chemin complet'
    
    def get_queryset(self, request):
        """Optimise les requêtes avec select_related"""
        return super().get_queryset(request).select_related('owner', 'parent')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Personnalise les champs de clé étrangère"""
        if db_field.name == "parent":
            # Éviter les références circulaires en excluant l'objet actuel
            if request.resolver_match and request.resolver_match.kwargs.get('object_id'):
                kwargs["queryset"] = Folder.objects.exclude(
                    id=request.resolver_match.kwargs['object_id']
                )
        if db_field.name == "owner":
            kwargs["queryset"] = kwargs.get("queryset", db_field.related_model.objects.all()).order_by('email')
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    actions = ['make_shared', 'make_private']
    
    def make_shared(self, request, queryset):
        """Action pour rendre les dossiers partagés"""
        updated = queryset.update(is_shared=True)
        self.message_user(request, f'{updated} dossier(s) marqué(s) comme partagé(s).')
    make_shared.short_description = "Marquer comme partagés"
    
    def make_private(self, request, queryset):
        """Action pour rendre les dossiers privés"""
        updated = queryset.update(is_shared=False)
        self.message_user(request, f'{updated} dossier(s) marqué(s) comme privé(s).')
    make_private.short_description = "Marquer comme privés"