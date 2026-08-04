def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return (forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')) or None


def is_public_blog_request(request):
    return request.path.startswith('/blog/') or request.path.startswith('/api/blog/')
