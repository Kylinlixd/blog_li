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
    return (forwarded.split(',')[0].strip() if forwarded else remote_addr) or None


def is_public_blog_request(request):
    return request.path.startswith('/blog/') or request.path.startswith('/api/blog/')
