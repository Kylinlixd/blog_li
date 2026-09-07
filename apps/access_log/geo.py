"""360 IP ownership lookup with persistent cache and offline fallback."""
import ipaddress
import re
from datetime import timedelta

import requests
from django.utils import timezone
from .models import IpGeoCache, IpGeoRecord

EMPTY = dict(country='', region='', city='', isp='', source='', matched=False)
URL = 'http://ip.360.cn/IPQuery/ipquery'


def parse_location(data):
    if not isinstance(data, str) or not data.strip():
        return None
    location, _, isp = data.strip().partition('\t')
    if location.strip() in {'未知', '未知地区', '保留地址'}:
        return None
    region = re.match(r'^(.*?(?:省|自治区|特别行政区)|北京|上海|天津|重庆)(.*)$', location)
    if region:
        province, city = region.groups()
        if province in {'北京', '上海', '天津', '重庆'}:
            province += '市'
            city = location[len(province):] or province
    else:
        province, city = location, ''
    return dict(country='', region=province[:120], city=city[:120], isp=isp.strip()[:160],
                location=location, source='360', matched=True)


def offline_geo(ip, records=None):
    best, match = -1, None
    for row in records if records is not None else IpGeoRecord.objects.values('network', 'country', 'region', 'city', 'isp', 'source', 'version'):
        try:
            network = ipaddress.ip_network(row['network'], strict=False)
            if ip in network and network.prefixlen > best:
                best, match = network.prefixlen, row
        except ValueError:
            continue
    return {**match, 'matched': True} if match else dict(EMPTY)


def lookup_geo(value, force=False, allow_remote=True, cache_rows=None, records=None):
    try:
        ip = ipaddress.ip_address((value or '').strip())
    except ValueError:
        return None
    cached = cache_rows.get(str(ip)) if cache_rows is not None else IpGeoCache.objects.filter(ip_address=str(ip)).first()
    if cached and not force and (not allow_remote or cached.expires_at > timezone.now()):
        return cached.data if cached.data.get('matched') else offline_geo(ip, records)
    fallback = (cached.data if cached and cached.data.get('matched') else offline_geo(ip, records))
    if not ip.is_global or ip.is_multicast:
        if fallback['matched']:
            return fallback
        return {**EMPTY, 'region': '回环' if ip.is_loopback else '内网' if ip.is_private else '保留地址', 'source': 'local', 'matched': True}
    if not allow_remote:
        return fallback
    try:
        response = requests.post(URL, data={'ip': str(ip)}, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'http://ip.360.cn/'}, timeout=(2, 3))
        response.raise_for_status()
        payload = response.json()  # JSON decoding handles the provider's Unicode escapes.
        geo = parse_location(payload.get('data')) if isinstance(payload, dict) and payload.get('errno') == 0 else None
    except (requests.RequestException, ValueError):
        geo = None
    IpGeoCache.objects.update_or_create(ip_address=str(ip), defaults={
        'data': geo or fallback,
        'expires_at': timezone.now() + (timedelta(days=30) if geo else timedelta(minutes=10)),
        'lookup_ok': bool(geo),
    })
    return geo or fallback
