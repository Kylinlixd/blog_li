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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['-created_at']), models.Index(fields=['ip_address', '-created_at'])]

    @classmethod
    def purge_expired(cls, retention_days=90):
        cutoff = timezone.now() - timedelta(days=max(1, int(retention_days)))
        return cls.objects.filter(created_at__lt=cutoff).delete()
