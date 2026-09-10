from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class AccessLog(models.Model):
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255)
    status_code = models.PositiveSmallIntegerField()
    user_agent = models.CharField(max_length=500, blank=True)
    device_type = models.CharField(max_length=20, default='other')
    device_model = models.CharField(max_length=120, default='未识别设备')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    security_rule = models.ForeignKey('IpSecurityRule', null=True, blank=True, on_delete=models.SET_NULL, related_name='access_logs')
    security_action = models.CharField(max_length=24, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['-created_at']), models.Index(fields=['ip_address', '-created_at'])]

    @classmethod
    def purge_expired(cls, retention_days=90):
        cutoff = timezone.now() - timedelta(days=max(1, int(retention_days)))
        return cls.objects.filter(created_at__lt=cutoff).delete()


class IpGeoRecord(models.Model):
    """Offline CIDR ownership table imported through load_ip_geo."""
    network = models.CharField(max_length=64, unique=True, help_text="CIDR 网段")
    country = models.CharField(max_length=100, blank=True, default="")
    region = models.CharField(max_length=120, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    isp = models.CharField(max_length=160, blank=True, default="")
    source = models.CharField(max_length=64, blank=True, default="")
    version = models.CharField(max_length=32, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["network"]


class IpSecurityRule(models.Model):
    RULE_TYPE_CHOICES = (
        ("whitelist", "可信白名单"),
        ("blacklist", "恶意黑名单"),
        ("ban", "封禁"),
        ("rate_limit", "限流"),
    )
    ATTACK_LEVEL_CHOICES = (
        ("low", "低"),
        ("medium", "中"),
        ("high", "高"),
        ("critical", "严重"),
    )
    STATUS_CHOICES = (
        ("active", "生效"),
        ("revoked", "已撤销"),
    )

    target = models.CharField(max_length=64, db_index=True, help_text="IP 或 CIDR")
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES)
    attack_level = models.CharField(
        max_length=12, choices=ATTACK_LEVEL_CHOICES, default="medium"
    )
    requests = models.PositiveIntegerField(null=True, blank=True, help_text="限流请求数")
    window_seconds = models.PositiveIntegerField(null=True, blank=True, help_text="限流窗口秒数")
    expires_at = models.DateTimeField(null=True, blank=True)
    is_permanent = models.BooleanField(default=False)
    reason = models.CharField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="active")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="security_rules_created",
    )
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="security_rules_revoked",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class IpRateBucket(models.Model):
    rule = models.ForeignKey(
        IpSecurityRule, on_delete=models.CASCADE, related_name="rate_buckets"
    )
    ip_address = models.GenericIPAddressField()
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["rule", "ip_address", "window_start"],
                name="unique_ip_rate_window",
            )
        ]


class IpGeoCache(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    data = models.JSONField(default=dict)
    lookup_ok = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)
