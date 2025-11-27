from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.common'
    label = 'common'
    
    def ready(self):
        """Import signals when app is ready."""
        print("DEBUG: CommonConfig.ready() called")
        import apps.common.signals  # noqa

