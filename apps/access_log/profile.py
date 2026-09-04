"""IP classification, geo fallback and behavior profile helpers."""

import ipaddress
from datetime import timedelta

from django.db.models import Count, Max, Min, Q
from django.utils import timezone

from .models import AccessLog, IpGeoRecord, IpSecurityRule


SCOPE_LABELS = {
    "public": "公网",
    "private": "内网",
    "loopback": "回环",
    "link_local": "链路本地",
    "reserved": "保留",
    "multicast": "组播",
    "unspecified": "未指定",
    "unknown": "未知",
}


def classify_ip(value):
    value = (value or "").strip()
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return {
            "ip_address": None,
            "version": 0,
            "scope": "unknown",
            "scope_label": "未知",
            "ip_type": "未知",
            "is_public": False,
        }

    if ip.is_loopback:
        scope = "loopback"
    elif ip.is_private:
        scope = "private"
    elif ip.is_global:
        scope = "public"
    elif ip.is_link_local:
        scope = "link_local"
    elif ip.is_multicast:
        scope = "multicast"
    elif ip.is_reserved:
        scope = "reserved"
    elif ip.is_unspecified:
        scope = "unspecified"
    else:
        scope = "public"

    return {
        "ip_address": str(ip),
        "version": ip.version,
        "scope": scope,
        "scope_label": SCOPE_LABELS[scope],
        "ip_type": f"{SCOPE_LABELS[scope]} IPv{ip.version}",
        "is_public": ip.is_global,
    }


def lookup_geo(value):
    try:
        ip = ipaddress.ip_address((value or "").strip())
    except ValueError:
        return None

    records = list(IpGeoRecord.objects.values(
        "network", "country", "region", "city", "isp", "source", "version"
    ))
    best = None
    for record in records:
        try:
            network = ipaddress.ip_network(record["network"], strict=False)
        except ValueError:
            continue
        if ip in network and (best is None or network.prefixlen > best.prefixlen):
            best = network
            matched = record
    if best is None:
        return {
            "country": "",
            "region": "",
            "city": "",
            "isp": "",
            "source": "",
            "matched": False,
        }
    return {**matched, "matched": True}


def _active_rules(value):
    try:
        ip = ipaddress.ip_address((value or "").strip())
    except ValueError:
        return []
    now = timezone.now()
    priority = {"whitelist": 0, "blacklist": 1, "ban": 2, "rate_limit": 3}
    rules = []
    for rule in IpSecurityRule.objects.filter(status="active").select_related("created_by"):
        if rule.expires_at and rule.expires_at <= now:
            continue
        try:
            target = ipaddress.ip_network(rule.target, strict=False)
        except ValueError:
            try:
                target = ipaddress.ip_network(f"{rule.target}/32" if ":" not in rule.target else f"{rule.target}/128", strict=False)
            except ValueError:
                continue
        if ip in target:
            rules.append((priority.get(rule.rule_type, 9), rule.created_at, rule))
    rules.sort(key=lambda item: (item[0], item[1], item[2].id))
    return [item[2] for item in rules]


def _risk(now, logs):
    recent_minute = logs.filter(created_at__gte=now - timedelta(minutes=1)).count()
    recent_hour = logs.filter(created_at__gte=now - timedelta(hours=1)).count()
    auth_failures = logs.filter(
        path__icontains="/auth/", status_code__in=[400, 401, 403]
    ).count()
    client_errors = logs.filter(status_code__gte=400, status_code__lt=500).count()
    server_errors = logs.filter(status_code__gte=500, status_code__lt=600).count()
    write_count = logs.filter(method__in=["POST", "PUT", "PATCH", "DELETE"]).count()
    path_count = logs.values("path").distinct().count()
    total = logs.count()

    reasons = []
    score = 0
    if auth_failures >= 5:
        score += 56
        reasons.append("认证失败集中")
    elif auth_failures >= 2:
        score += 16
        reasons.append("存在认证失败")
    if recent_minute >= 60:
        score += 26
        reasons.append("短窗口高频")
    elif recent_minute >= 30:
        score += 14
        reasons.append("访问频率偏高")
    if recent_hour and recent_hour >= 300:
        score += 14
        reasons.append("小时窗口请求量大")
    if total and (client_errors + server_errors) / max(total, 1) >= 0.3:
        score += 12
        reasons.append("错误响应占比高")
    if total and write_count / max(total, 1) >= 0.6 and total >= 10:
        score += 10
        reasons.append("写操作集中")
    if path_count >= 30:
        score += 10
        reasons.append("访问路径扩散")

    score = max(0, min(100, score))
    if score >= 75:
        level = "critical"
    elif score >= 50:
        level = "high"
    elif score >= 25:
        level = "medium"
    elif score >= 10:
        level = "low"
    else:
        level = "normal"
    return {
        "risk_score": score,
        "risk_level": level,
        "risk_reasons": reasons or ["未发现明显异常"],
        "recent_1m": recent_minute,
        "recent_1h": recent_hour,
        "auth_failures": auth_failures,
        "client_errors": client_errors,
        "server_errors": server_errors,
        "write_count": write_count,
        "unique_paths": path_count,
    }


def build_ip_profile(value, now=None):
    now = now or timezone.now()
    classification = classify_ip(value)
    if not classification["ip_address"]:
        return {
            **classification,
            "geo": None,
            "behavior": None,
            "risk_score": 0,
            "risk_level": "unknown",
            "risk_reasons": ["IP 无法解析"],
            "rules": [],
        }

    logs = AccessLog.objects.filter(ip_address=classification["ip_address"])
    summary = logs.aggregate(total=Count("id"), first_seen=Min("created_at"), last_seen=Max("created_at"))
    risk = _risk(now, logs)
    geo = lookup_geo(classification["ip_address"])
    rules = _active_rules(classification["ip_address"])
    rule_summary = [
        {
            "id": rule.id,
            "rule_type": rule.rule_type,
            "attack_level": rule.attack_level,
            "requests": rule.requests,
            "window_seconds": rule.window_seconds,
            "expires_at": rule.expires_at,
            "is_permanent": rule.is_permanent,
            "reason": rule.reason,
            "status": rule.status,
        }
        for rule in rules
    ]
    return {
        **classification,
        "geo": geo,
        "behavior": {
            "total_requests": summary["total"] or 0,
            "first_seen": summary["first_seen"],
            "last_seen": summary["last_seen"],
            "success_count": logs.filter(status_code__lt=400).count(),
            "risk": risk,
        },
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"],
        "risk_reasons": risk["risk_reasons"],
        "rules": rule_summary,
    }
