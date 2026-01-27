from django.apps import AppConfig


class DatingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dating'
    from .firebase_utils import init_firebase
    init_firebase()
