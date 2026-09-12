import re


def _version(value):
    """Keep the first two version components for compact, readable labels."""
    parts = re.findall(r'\d+', value or '')[:2]
    return '.'.join(parts)


def parse_client_metadata(user_agent):
    """Return display-safe (operating system, browser) labels from a UA string."""
    ua = user_agent or ''

    if re.search(r'Windows NT', ua, re.I):
        match = re.search(r'Windows NT\s*([\d.]+)', ua, re.I)
        os_name = f"Windows {_version(match.group(1))}" if match else 'Windows'
    elif re.search(r'iPhone|iPad', ua, re.I):
        match = re.search(r'(?:iPhone OS|CPU OS)\s*([\d_]+)', ua, re.I)
        os_name = f"iOS {_version(match.group(1).replace('_', '.'))}" if match else 'iOS'
    elif re.search(r'Android', ua, re.I):
        match = re.search(r'Android\s*([\d.]+)', ua, re.I)
        os_name = f"Android {_version(match.group(1))}" if match else 'Android'
    elif re.search(r'Mac OS X', ua, re.I):
        # Chrome/Safari intentionally report a compatibility value such as
        # 10.15.7 even on newer macOS releases, so the UA version is not
        # reliable enough to show in a public comment label.
        os_name = 'macOS'
    elif re.search(r'Linux', ua, re.I):
        os_name = 'Linux'
    else:
        os_name = ''

    browser_patterns = (
        ('Edge', r'(?:Edg|Edge)/([\d.]+)'),
        ('Opera', r'(?:OPR|Opera)/([\d.]+)'),
        ('Chrome', r'(?:Chrome|CriOS)/([\d.]+)'),
        ('Firefox', r'(?:Firefox|FxiOS)/([\d.]+)'),
        ('Safari', r'Version/([\d.]+).*Safari/'),
        ('IE', r'(?:MSIE\s|rv:)([\d.]+).*Trident/'),
    )
    browser_name = ''
    browser_version = ''
    for name, pattern in browser_patterns:
        match = re.search(pattern, ua, re.I)
        if match:
            browser_name = name
            browser_version = _version(match.group(1))
            break
    browser = f'{browser_name}{browser_version}' if browser_name else ''
    return os_name, browser
