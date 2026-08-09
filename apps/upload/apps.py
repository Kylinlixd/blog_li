from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured


class UploadConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.upload'

    def ready(self):
        from . import checks

        missing = checks.missing_xion_settings()
        if missing:
            raise ImproperlyConfigured(
                "启用 AstraStoreXion 时缺少必要配置: " + ", ".join(missing)
            )
