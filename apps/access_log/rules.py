"""Validation, precedence and rate bucket helpers for security rules."""

import ipaddress
from datetime import datetime, timezone as datetime_timezone

from django.db.models import F
from django.utils import timezone

from .models import IpRateBucket


RULE_PRIORITY = {"whitelist": 0, "blacklist": 1, "ban": 2, "rate_limit": 3}


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


def active_rules_for_ip(value, now=None):
    try:
        ip = ipaddress.ip_address((value or "").strip())
    except ValueError:
        return []

    from .models import IpSecurityRule

    now = now or timezone.now()
    rules = []
    for rule in IpSecurityRule.objects.filter(status="active").iterator():
        if rule.expires_at and rule.expires_at <= now:
            continue
        try:
            network = ipaddress.ip_network(rule.target, strict=False)
        except ValueError:
            continue
        if ip in network:
            rules.append(rule)
    rules.sort(key=lambda rule: (RULE_PRIORITY.get(rule.rule_type, 99), -rule.created_at.timestamp()))
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
