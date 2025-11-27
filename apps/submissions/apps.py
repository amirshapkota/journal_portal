from django.apps import AppConfig


class SubmissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.submissions'
    label = 'submissions'
    
    def ready(self):
        """Import signals when app is ready."""
        import apps.submissions.signals  # noqa

