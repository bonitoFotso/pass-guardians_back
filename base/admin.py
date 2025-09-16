from django.contrib import admin
from .models import AppSettings


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'user', 
        'theme', 
        'auto_lock_timeout', 
        'clipboard_clear_timeout',
        'enable_biometric',
        'breach_monitoring',
        'created_at'
    ]
    
    list_filter = [
        'theme',
        'auto_lock_timeout',
        'clipboard_clear_timeout',
        'enable_biometric',
        'show_password_strength',
        'auto_fill_enabled',
        'breach_monitoring',
        'login_notifications',
        'export_format',
        'created_at'
    ]
    
    search_fields = [
        'user__email',
        'user__username',
        'user__first_name',
        'user__last_name'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user',)
        }),
        ('Apparence', {
            'fields': ('theme',)
        }),
        ('Sécurité', {
            'fields': (
                'auto_lock_timeout',
                'clipboard_clear_timeout',
                'enable_biometric'
            )
        }),
        ('Interface', {
            'fields': (
                'show_password_strength',
                'auto_fill_enabled'
            )
        }),
        ('Notifications', {
            'fields': (
                'breach_monitoring',
                'login_notifications'
            )
        }),
        ('Export', {
            'fields': ('export_format',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Optionnel : actions personnalisées
    actions = ['reset_to_default_settings']
    
    def reset_to_default_settings(self, request, queryset):
        """Réinitialise les paramètres aux valeurs par défaut"""
        updated = 0
        for settings in queryset:
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
            updated += 1
        
        self.message_user(
            request,
            f"{updated} paramètres ont été réinitialisés aux valeurs par défaut."
        )
    
    reset_to_default_settings.short_description = "Réinitialiser aux paramètres par défaut"
    
    # Optionnel : personnalisation de l'affichage des choix
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Personnalisation des widgets ou validations si nécessaire
        if 'auto_lock_timeout' in form.base_fields:
            form.base_fields['auto_lock_timeout'].help_text = "Délai avant verrouillage automatique"
        
        if 'clipboard_clear_timeout' in form.base_fields:
            form.base_fields['clipboard_clear_timeout'].help_text = "Délai avant effacement du presse-papiers"
            
        return form