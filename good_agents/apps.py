from django.apps import AppConfig


class GoodAgentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'good_agents'
    verbose_name = 'Good Agents — 114 Principle Lenses'

    def ready(self):
        from good_agents import signals  # noqa: F401
