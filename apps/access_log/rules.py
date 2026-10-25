"""Validation, precedence and rate bucket helpers for security rules."""

import ipaddress
from datetime import datetime, timezone as datetime_timezone

from django.core.cache import cache
from django.db.models import F
from django.utils import timezone

from .models import IpRateBucket


RULE_PRIORITY = {"whitelist": 0, "blacklist": 1, "ban": 2, "rate_limit": 3}

# 规则表是人工维护的小表，但中间件每个 /api/ 请求都要查一次；
# 解析结果（规则实例 + 网络）整表缓存，增删改时由信号失效。
RULES_CACHE_KEY = "access_log:active_rules:v1"
RULES_CACHE_TTL = 30  # 秒，信号失效前的兜底窗口


def normalize_target(value):
    value = (value or "").strip()
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError as exc:
            raise ValueError("请输入有效的 IP 或 CIDR") from exc
        return str(network)
    return str(ip)


def validate_rate_window(rule_type, requests, window_seconds):
    if rule_type != "rate_limit":
        return
    if not requests or requests < 1 or requests > 1_000_000:
        raise ValueError("限流请求数必须为 1 到 1000000")
    if not window_seconds or window_seconds < 1 or window_seconds > 86400:
        raise ValueError("限流窗口必须为 1 到 86400 秒")


def _load_active_rules():
    """加载并预解析全部生效规则，按优先级排序。返回 [(rule, network)]。"""
    from .models import IpSecurityRule

    now = timezone.now()
    entries = []
    for rule in IpSecurityRule.objects.filter(status="active").iterator():
        if rule.expires_at and rule.expires_at <= now:
            continue
        try:
            network = ipaddress.ip_network(rule.target, strict=False)
        except ValueError:
            continue
        entries.append((rule, network))
    entries.sort(key=lambda pair: (RULE_PRIORITY.get(pair[0].rule_type, 99), -pair[0].created_at.timestamp()))
    return entries


def get_cached_active_rules():
    entries = cache.get(RULES_CACHE_KEY)
    if entries is None:
        entries = _load_active_rules()
        cache.set(RULES_CACHE_KEY, entries, RULES_CACHE_TTL)
    return entries


def invalidate_active_rules_cache():
    cache.delete(RULES_CACHE_KEY)


def active_rules_for_ip(value, now=None):
    try:
        ip = ipaddress.ip_address((value or "").strip())
    except ValueError:
        return []

    # get_cached_active_rules 已按优先级排序，这里的过滤保持原有顺序
    now = now or timezone.now()
    rules = []
    for rule, network in get_cached_active_rules():
        # 缓存窗口内可能刚好过期，按时间再过滤一次，不回源
        if rule.expires_at and rule.expires_at <= now:
            continue
        if ip in network:
            rules.append(rule)
    return rules


def precedence_for_ip(value, now=None):
    rules = active_rules_for_ip(value, now)
    return rules[0] if rules else None


def increment_rate_bucket(rule, ip_address, now=None):
    now = now or timezone.now()
    window_seconds = max(1, rule.window_seconds or 60)
    window_epoch = (int(now.timestamp()) // window_seconds) * window_seconds
    window_start = datetime.fromtimestamp(
        window_epoch,
        tz=datetime_timezone.utc,
    )
    bucket, _ = IpRateBucket.objects.get_or_create(
        rule=rule,
        ip_address=ip_address,
        window_start=window_start,
        defaults={"count": 0},
    )
    IpRateBucket.objects.filter(pk=bucket.pk).update(count=F("count") + 1)
    bucket.refresh_from_db(fields=["count"])
    return bucket.count


def revoke_rule(rule, user):
    rule.status = "revoked"
    rule.revoked_by = user
    rule.revoked_at = timezone.now()
    rule.save(update_fields=["status", "revoked_by", "revoked_at", "updated_at"])
    return rule
