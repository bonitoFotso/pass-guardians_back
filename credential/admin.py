from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django import forms

from .models import Category, Credential, PasswordHistory


class CredentialAdminForm(forms.ModelForm):
    """Formulaire personnalisé pour l'admin des credentials"""
    password_plain = forms.CharField(
        widget=forms.PasswordInput(),
        required=False,
        help_text="Laissez vide pour conserver le mot de passe actuel",
        label="Nouveau mot de passe"
    )
    
    notes_plain = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 50}),
        required=False,
        help_text="Notes en clair (seront chiffrées automatiquement)",
        label="Notes"
    )
    
    class Meta:
        model = Credential
        fields = '__all__'
        exclude = ('password_encrypted', 'notes_encrypted')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si on modifie un credential existant, pré-remplir les notes
        if self.instance.pk:
            self.fields['notes_plain'].initial = self.instance.decrypt_notes()
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Gérer le mot de passe
        password_plain = self.cleaned_data.get('password_plain')
        if password_plain:
            instance.encrypt_password(password_plain)
            instance.password_changed_at = timezone.now()
        
        # Gérer les notes
        notes_plain = self.cleaned_data.get('notes_plain', '')
        instance.encrypt_notes(notes_plain)
        
        if commit:
            instance.save()
        return instance


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon_display', 'color_display', 'is_system', 'credential_count', 'created_at']
    list_filter = ['is_system', 'icon', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'icon', 'color', 'is_system')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def icon_display(self, obj):
        """Affiche l'icône avec son nom"""
        return f"{obj.get_icon_display()}"
    icon_display.short_description = "Icône"
    
    def color_display(self, obj):
        """Affiche la couleur avec un aperçu visuel"""
        return format_html(
            '<span style="background-color: {}; padding: 5px 10px; color: white; border-radius: 3px;">{}</span>',
            obj.color,
            obj.color
        )
    color_display.short_description = "Couleur"
    
    def credential_count(self, obj):
        """Compte le nombre de credentials dans cette catégorie"""
        count = obj.credential_set.count()
        if count > 0:
            url = reverse('admin:credentials_credential_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}">{} credential(s)</a>', url, count)
        return "0"
    credential_count.short_description = "Credentials"
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            credential_count=Count('credential')
        )


class PasswordHistoryInline(admin.TabularInline):
    model = PasswordHistory
    extra = 0
    readonly_fields = ['password_hash', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Credential)
class CredentialAdmin(admin.ModelAdmin):
    form = CredentialAdminForm
    list_display = [
        'name', 'owner', 'username', 'category', 'folder',
        'is_favorite', 'is_shared', 'password_strength_display',
        'last_used_display', 'created_at'
    ]
    list_filter = [
        'is_favorite', 'is_shared', 'auto_generated', 'category',
        'created_at', 'last_used_at', 'password_changed_at'
    ]
    search_fields = ['name', 'username', 'url', 'owner__email', 'owner__username']
    readonly_fields = [
        'created_at', 'updated_at', 'last_used_at',
        'password_changed_at', 'password_strength', 'decrypted_password_display'
    ]
    filter_horizontal = []
    raw_id_fields = ['owner', 'folder']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'owner', 'username', 'url')
        }),
        ('Sécurité', {
            'fields': (
                'password_plain', 'decrypted_password_display',
                'password_strength', 'password_changed_at', 'auto_generated'
            )
        }),
        ('Notes', {
            'fields': ('notes_plain',),
            'classes': ('collapse',)
        }),
        ('Organisation', {
            'fields': ('category', 'folder', 'is_favorite', 'is_shared')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'last_used_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PasswordHistoryInline]
    
    def password_strength_display(self, obj):
        """Affiche la force du mot de passe avec une barre colorée"""
        strength = obj.password_strength
        if strength >= 80:
            color = '#28a745'  # Vert
            text = 'Fort'
        elif strength >= 60:
            color = '#ffc107'  # Jaune
            text = 'Moyen'
        elif strength >= 40:
            color = '#fd7e14'  # Orange
            text = 'Faible'
        else:
            color = '#dc3545'  # Rouge
            text = 'Très faible'
        
        return format_html(
            '<div style="display: flex; align-items: center;">'
            '<div style="width: 50px; height: 10px; background-color: #e9ecef; margin-right: 10px; border-radius: 5px;">'
            '<div style="width: {}%; height: 100%; background-color: {}; border-radius: 5px;"></div>'
            '</div>'
            '<span>{} ({}%)</span>'
            '</div>',
            strength, color, text, strength
        )
    password_strength_display.short_description = "Force du mot de passe"
    
    def last_used_display(self, obj):
        """Affiche la dernière utilisation de manière lisible"""
        if not obj.last_used_at:
            return format_html('<span style="color: #6c757d;">Jamais utilisé</span>')
        
        now = timezone.now()
        diff = now - obj.last_used_at
        
        if diff.days == 0:
            return format_html('<span style="color: #28a745;">Aujourd\'hui</span>')
        elif diff.days == 1:
            return format_html('<span style="color: #28a745;">Hier</span>')
        elif diff.days <= 7:
            return format_html('<span style="color: #ffc107;">Il y a {} jours</span>', diff.days)
        elif diff.days <= 30:
            weeks = diff.days // 7
            return format_html('<span style="color: #fd7e14;">Il y a {} semaine(s)</span>', weeks)
        else:
            months = diff.days // 30
            return format_html('<span style="color: #dc3545;">Il y a {} mois</span>', months)
    
    last_used_display.short_description = "Dernière utilisation"
    
    def decrypted_password_display(self, obj):
        """Affiche le mot de passe déchiffré (pour l'admin seulement)"""
        if obj.pk:  # L'objet existe déjà
            try:
                password = obj.decrypt_password()
                if password:
                    return format_html(
                        '<input type="password" value="{}" readonly style="width: 200px;" '
                        'onclick="this.type=this.type===\'password\'?\'text\':\'password\'" '
                        'title="Cliquez pour afficher/masquer">',
                        password
                    )
                return "Aucun mot de passe"
            except Exception as e:
                return format_html('<span style="color: red;">Erreur de déchiffrement: {}</span>', str(e))
        return "Sauvegardez d'abord l'objet"
    
    decrypted_password_display.short_description = "Mot de passe (cliquez pour révéler)"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner', 'category', 'folder')
    
    def save_model(self, request, obj, form, change):
        """Personnalise la sauvegarde pour gérer le chiffrement"""
        # Si c'est une création et qu'on a un mot de passe en clair, le chiffrer
        if hasattr(form, 'cleaned_data') and 'password' in form.cleaned_data:
            obj.encrypt_password(form.cleaned_data['password'])
        
        super().save_model(request, obj, form, change)


@admin.register(PasswordHistory)
class PasswordHistoryAdmin(admin.ModelAdmin):
    list_display = ['credential', 'password_hash_short', 'created_at']
    list_filter = ['created_at']
    search_fields = ['credential__name', 'credential__owner__email']
    readonly_fields = ['credential', 'password_hash', 'created_at', 'updated_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def password_hash_short(self, obj):
        """Affiche une version courte du hash"""
        return f"{obj.password_hash[:20]}..." if len(obj.password_hash) > 20 else obj.password_hash
    password_hash_short.short_description = "Hash (tronqué)"
    
    def has_add_permission(self, request):
        """Empêche l'ajout manuel d'historique"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Empêche la modification de l'historique"""
        return False

