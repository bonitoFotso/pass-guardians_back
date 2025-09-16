from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import AppSettings

User = get_user_model()


class AppSettingsSerializer(serializers.ModelSerializer):
    """Serializer pour les paramètres d'application"""
    
    # Champs en lecture seule
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    # Affichage des labels pour les choix
    theme_display = serializers.CharField(source='get_theme_display', read_only=True)
    auto_lock_timeout_display = serializers.CharField(source='get_auto_lock_timeout_display', read_only=True)
    clipboard_clear_timeout_display = serializers.CharField(source='get_clipboard_clear_timeout_display', read_only=True)
    export_format_display = serializers.CharField(source='get_export_format_display', read_only=True)
    
    class Meta:
        model = AppSettings
        fields = [
            'id',
            'user',
            'user_email',
            'user_username',
            # Apparence
            'theme',
            'theme_display',
            # Sécurité
            'auto_lock_timeout',
            'auto_lock_timeout_display',
            'clipboard_clear_timeout',
            'clipboard_clear_timeout_display',
            'enable_biometric',
            # Interface
            'show_password_strength',
            'auto_fill_enabled',
            # Notifications
            'breach_monitoring',
            'login_notifications',
            # Export
            'export_format',
            'export_format_display',
            # Métadonnées
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate_auto_lock_timeout(self, value):
        """Validation du délai de verrouillage automatique"""
        valid_values = [choice[0] for choice in AppSettings.TimeoutChoices.choices]
        if value not in valid_values:
            raise serializers.ValidationError(
                f"Valeur invalide. Choisissez parmi: {valid_values}"
            )
        return value
    
    def validate_clipboard_clear_timeout(self, value):
        """Validation du délai d'effacement du presse-papiers"""
        valid_values = [choice[0] for choice in AppSettings.ClipboardTimeoutChoices.choices]
        if value not in valid_values:
            raise serializers.ValidationError(
                f"Valeur invalide. Choisissez parmi: {valid_values}"
            )
        return value
    
    def validate_theme(self, value):
        """Validation du thème"""
        valid_values = [choice[0] for choice in AppSettings.ThemeChoices.choices]
        if value not in valid_values:
            raise serializers.ValidationError(
                f"Valeur invalide. Choisissez parmi: {valid_values}"
            )
        return value
    
    def validate_export_format(self, value):
        """Validation du format d'export"""
        valid_values = [choice[0] for choice in AppSettings.ExportFormatChoices.choices]
        if value not in valid_values:
            raise serializers.ValidationError(
                f"Valeur invalide. Choisissez parmi: {valid_values}"
            )
        return value


class AppSettingsUpdateSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les mises à jour partielles"""
    
    class Meta:
        model = AppSettings
        fields = [
            'theme',
            'auto_lock_timeout',
            'clipboard_clear_timeout',
            'enable_biometric',
            'show_password_strength',
            'auto_fill_enabled',
            'breach_monitoring',
            'login_notifications',
            'export_format'
        ]
    
    def validate(self, attrs):
        """Validation globale"""
        # Exemple de validation croisée
        if attrs.get('enable_biometric', False) and attrs.get('auto_lock_timeout') == 0:
            raise serializers.ValidationError(
                "Le verrouillage automatique ne peut pas être désactivé si la biométrie est activée."
            )
        return attrs


class AppSettingsChoicesSerializer(serializers.Serializer):
    """Serializer pour retourner les choix disponibles"""
    
    theme_choices = serializers.SerializerMethodField()
    timeout_choices = serializers.SerializerMethodField()
    clipboard_timeout_choices = serializers.SerializerMethodField()
    export_format_choices = serializers.SerializerMethodField()
    
    def get_theme_choices(self, obj):
        return [{'value': choice[0], 'label': choice[1]} for choice in AppSettings.ThemeChoices.choices]
    
    def get_timeout_choices(self, obj):
        return [{'value': choice[0], 'label': choice[1]} for choice in AppSettings.TimeoutChoices.choices]
    
    def get_clipboard_timeout_choices(self, obj):
        return [{'value': choice[0], 'label': choice[1]} for choice in AppSettings.ClipboardTimeoutChoices.choices]
    
    def get_export_format_choices(self, obj):
        return [{'value': choice[0], 'label': choice[1]} for choice in AppSettings.ExportFormatChoices.choices]


class AppSettingsCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création (avec valeurs par défaut)"""
    
    class Meta:
        model = AppSettings
        fields = [
            'user',
            'theme',
            'auto_lock_timeout',
            'clipboard_clear_timeout',
            'enable_biometric',
            'show_password_strength',
            'auto_fill_enabled',
            'breach_monitoring',
            'login_notifications',
            'export_format'
        ]
    
    def create(self, validated_data):
        """Création avec l'utilisateur courant si non spécifié"""
        if 'user' not in validated_data:
            validated_data['user'] = self.context['request'].user
        return super().create(validated_data)