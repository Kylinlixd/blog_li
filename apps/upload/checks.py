from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def check_xion_storage_settings(app_configs, **kwargs):
    if not settings.XION_STORAGE_ENABLED:
        return []
    missing = []
    if not settings.XION_BASE_URL:
        missing.append("XION_BASE_URL")
    if not settings.XION_SERVICE_TOKEN:
        missing.append("XION_SERVICE_TOKEN")
    if not missing:
        return []
    return [Error(
        "启用 AstraStoreXion 时缺少必要配置: " + ", ".join(missing),
        hint="在受限的服务环境文件中设置变量，不要提交令牌。",
        id="upload.E001",
    )]
