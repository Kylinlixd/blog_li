import ipaddress

from django.conf import settings


def get_client_ip(request):
    remote_addr = request.META.get('REMOTE_ADDR')
    trusted_proxies = set(getattr(settings, 'TRUSTED_PROXY_IPS', ()))
    try:
        remote_is_trusted = ipaddress.ip_address(remote_addr or '') in {
            ipaddress.ip_address(value) for value in trusted_proxies
        }
    except ValueError:
        remote_is_trusted = False

    if not remote_is_trusted:
        return remote_addr or None

    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        # 信任链只有一跳（nginx → gunicorn）。nginx 的 $proxy_add_x_forwarded_for
        # 把真实来源追加在末尾，前面的条目全部是客户端自报、可任意伪造，
        # 因此只认最后一跳。
        last_hop = forwarded.split(',')[-1].strip()
        if last_hop:
            return last_hop
    return remote_addr or None


def is_public_blog_request(request):
    return request.path.startswith('/blog/') or request.path.startswith('/api/blog/')
