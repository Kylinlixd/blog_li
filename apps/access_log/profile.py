"""IP classification, geo fallback and behavior profile helpers."""

import ipaddress
from datetime import timedelta
from collections import defaultdict

from django.db.models import Count, Max, Min, Q
from django.utils import timezone

from .models import AccessLog, IpSecurityRule, IpGeoCache, IpGeoRecord
from .geo import lookup_geo


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


def _anomaly_level(failed_requests, total_requests):
    """Return the request failure anomaly level for one reporting window."""
    if not total_requests:
        return "normal"
    failure_rate = failed_requests / total_requests
    if failed_requests >= 100 and failure_rate >= 0.8:
        return "critical"
    if failed_requests >= 30 and failure_rate >= 0.5:
        return "high"
    if failed_requests >= 10 and failure_rate >= 0.3:
        return "medium"
    return "normal"


def _format_failure_reason(prefix, failed_requests, total_requests, error_rate):
    return f"{prefix}（失败 {failed_requests}/{total_requests}，{error_rate:.1f}%）"


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
        "is_public": ip.is_global and not ip.is_multicast,
    }


def _risk(now, logs):
    entries = list(logs.values('created_at', 'path', 'status_code', 'method')) if hasattr(logs, 'values') else logs
    recent_minute = sum(row['created_at'] >= now - timedelta(minutes=1) for row in entries)
    recent_hour = sum(row['created_at'] >= now - timedelta(hours=1) for row in entries)
    auth_failures = sum('/auth/' in row['path'] and row['status_code'] in (400, 401, 403) for row in entries)
    client_errors = sum(400 <= row['status_code'] < 500 for row in entries)
    server_errors = sum(500 <= row['status_code'] < 600 for row in entries)
    write_count = sum(row['method'] in ('POST', 'PUT', 'PATCH', 'DELETE') for row in entries)
    path_count = len({row['path'] for row in entries})
    total = len(entries)
    failed_requests = client_errors + server_errors
    raw_error_rate = failed_requests / total if total else 0
    error_rate = round(raw_error_rate * 100, 1)
    anomaly_level = _anomaly_level(failed_requests, total)

    reasons = []
    anomaly_reasons = []
    score = 0
    client_error_floor = 0
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
    client_error_level = _anomaly_level(client_errors, total)
    if client_error_level == "medium":
        client_error_floor = 25
        reasons.append(_format_failure_reason("客户端错误偏多", client_errors, total, client_errors / total * 100 if total else 0))
    elif client_error_level in ("high", "critical"):
        client_error_floor = 50
        reasons.append(_format_failure_reason("客户端错误集中", client_errors, total, client_errors / total * 100 if total else 0))
    if total and write_count / max(total, 1) >= 0.6 and total >= 10:
        score += 10
        reasons.append("写操作集中")
    if path_count >= 30:
        score += 10
        reasons.append("访问路径扩散")

    if anomaly_level != "normal":
        anomaly_prefix = "请求失败集中" if anomaly_level in ("high", "critical") else "请求失败偏多"
        anomaly_reasons.append(_format_failure_reason(anomaly_prefix, failed_requests, total, error_rate))
        if client_errors:
            if client_error_level != "normal":
                client_prefix = "客户端错误集中" if client_error_level in ("high", "critical") else "客户端错误偏多"
                anomaly_reasons.append(_format_failure_reason(client_prefix, client_errors, total, client_errors / total * 100))
        if server_errors and server_errors >= 10 and server_errors / total >= 0.3:
            anomaly_reasons.append(_format_failure_reason("服务端错误偏多，建议排查服务", server_errors, total, server_errors / total * 100))

    score = max(score, client_error_floor)

    score = max(0, min(100, score))
    if score >= 75:
        level = "critical"
    elif score >= 50:
        level = "high"
    elif score >= 25:
        level = "medium"
    else:
        level = "low"
    return {
        "risk_score": score,
        "risk_level": level,
        "risk_reasons": reasons or ["未发现明显IP安全风险"],
        "recent_1m": recent_minute,
        "recent_1h": recent_hour,
        "auth_failures": auth_failures,
        "client_errors": client_errors,
        "server_errors": server_errors,
        "write_count": write_count,
        "unique_paths": path_count,
        "total_requests": total,
        "failed_requests": failed_requests,
        "error_rate": error_rate,
        "anomaly_level": anomaly_level,
        "anomaly_reasons": anomaly_reasons,
    }


def build_ip_profiles(values, now=None, since=None, allow_remote=False):
    """Five DB reads for any collection size; provider calls are opt-in."""
    now = now or timezone.now()
    values = list(values)
    summaries = {row['ip_address']: row for row in AccessLog.objects.filter(ip_address__in=values).order_by()
                 .values('ip_address').annotate(total=Count('id'), first_seen=Min('created_at'), last_seen=Max('created_at'), success=Count('id', filter=Q(status_code__lt=400)))}
    recent = defaultdict(list)
    for row in AccessLog.objects.filter(ip_address__in=values, created_at__gte=since or now-timedelta(days=7), created_at__lte=now).order_by().values('ip_address', 'created_at', 'path', 'status_code', 'method'):
        recent[row['ip_address']].append(row)
    active = []
    for rule in IpSecurityRule.objects.filter(status='active').filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)):
        try:
            active.append((ipaddress.ip_network(rule.target, strict=False), rule))
        except ValueError:
            continue
    caches = {row.ip_address: row for row in IpGeoCache.objects.filter(ip_address__in=values)}
    records = list(IpGeoRecord.objects.values('network', 'country', 'region', 'city', 'isp', 'source', 'version'))
    profiles = []
    for value in values:
        classification = classify_ip(value)
        ip_value = classification['ip_address']
        if not ip_value:
            profiles.append({**classification, 'geo': None, 'behavior': None, 'risk_score': 0, 'risk_level': 'unknown', 'risk_reasons': ['IP 无法解析'], 'rules': []})
            continue
        ip = ipaddress.ip_address(ip_value)
        summary = summaries.get(ip_value, {})
        risk = _risk(now, recent[ip_value])
        rules = [rule for network, rule in active if ip in network]
        if any(rule.rule_type == 'whitelist' for rule in rules):
            risk.update(risk_score=0, risk_level='low', risk_reasons=['可信白名单，已豁免风险评级'])
        profiles.append({
            **classification,
            'geo': lookup_geo(ip_value, allow_remote=allow_remote, cache_rows=caches, records=records),
            'behavior': {'total_requests': summary.get('total', 0), 'first_seen': summary.get('first_seen'), 'last_seen': summary.get('last_seen'), 'success_count': summary.get('success', 0), 'risk': risk},
            'risk_score': risk['risk_score'], 'risk_level': risk['risk_level'], 'risk_reasons': risk['risk_reasons'],
            'rules': [{key: getattr(rule, key) for key in ('id', 'rule_type', 'attack_level', 'requests', 'window_seconds', 'expires_at', 'is_permanent', 'reason', 'status')} for rule in rules],
        })
    return profiles


def build_ip_profile(value, now=None, allow_remote=True, since=None):
    return build_ip_profiles([value], now=now, since=since, allow_remote=allow_remote)[0]
