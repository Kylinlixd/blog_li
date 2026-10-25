from django.apps import AppConfig


class AccessLogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.access_log'
    verbose_name = '访问日志'

    def ready(self):
        from . import signals  # noqa: F401  规则增删改时失效 active rules 缓存
