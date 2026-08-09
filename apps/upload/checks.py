from django.conf import settings
from django.core.checks import Error, Tags, register


def missing_xion_settings():
    if not settings.XION_STORAGE_ENABLED:
        return []
    return [
        name
        for name, value in (
            ("XION_BASE_URL", settings.XION_BASE_URL),
            ("XION_SERVICE_TOKEN", settings.XION_SERVICE_TOKEN),
        )
        if not value
    ]


@register(Tags.security)
def check_xion_storage_settings(app_configs, **kwargs):
    missing = missing_xion_settings()
    if not missing:
        return []
    return [Error(
        "启用 AstraStoreXion 时缺少必要配置: " + ", ".join(missing),
        hint="在受限的服务环境文件中设置变量，不要提交令牌。",
        id="upload.E001",
    )]
