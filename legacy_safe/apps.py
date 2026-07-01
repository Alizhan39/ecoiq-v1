from django.apps import AppConfig


class LegacySafeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'legacy_safe'
    verbose_name = 'LegacySafe AI'
