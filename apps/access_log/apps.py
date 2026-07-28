from django.apps import AppConfig


class AccessLogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.access_log'
    verbose_name = '访问日志'
