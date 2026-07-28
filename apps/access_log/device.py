import re


def parse_user_agent(user_agent):
    """Return a conservative device type/model pair from a browser UA."""
    ua = user_agent or ''
    if re.search(r'iPad|Tablet', ua, re.I):
        if re.search(r'iPad', ua, re.I):
            return 'tablet', 'iPad'
        return 'tablet', 'Android 平板'
    if re.search(r'iPhone', ua, re.I):
        return 'mobile', 'iPhone'
    if re.search(r'Android', ua, re.I):
        match = re.search(r'Android[^;)]*;\s*([^;)]+)', ua, re.I)
        model = re.sub(r'\s+Build[/;].*$', '', match.group(1)).strip() if match else 'Android 手机'
        return 'mobile', model or 'Android 手机'
    if re.search(r'Windows NT', ua, re.I):
        return 'computer', 'Windows 电脑'
    if re.search(r'Macintosh|Mac OS X', ua, re.I):
        return 'computer', 'Mac 电脑'
    if re.search(r'Linux', ua, re.I):
        return 'computer', 'Linux 电脑'
    return 'other', '未识别设备'
