"""失效 active rules 缓存：任何规则变更都必须立即对中间件生效。"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import IpSecurityRule
from .rules import invalidate_active_rules_cache


@receiver(post_save, sender=IpSecurityRule)
@receiver(post_delete, sender=IpSecurityRule)
def invalidate_rules_cache_on_change(sender, **kwargs):
    invalidate_active_rules_cache()
