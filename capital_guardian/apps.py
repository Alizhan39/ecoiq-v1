from django.apps import AppConfig


class CapitalGuardianConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'capital_guardian'

    def ready(self):
        from capital_guardian import signals
        signals.connect()
