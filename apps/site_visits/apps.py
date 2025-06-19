from django.apps import AppConfig


class SiteVisitsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.site_visits'

    def ready(self):
        import apps.site_visits.signals  # noqa: F401
