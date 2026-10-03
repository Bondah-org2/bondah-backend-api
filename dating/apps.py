from django.apps import AppConfig


class DatingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dating'

    def ready(self):
        import dating.signals
        import dating.media_lifecycle  # noqa: F401  (registers media receivers)
