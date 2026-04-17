# -*- coding: utf-8 -*-
"""Syncher - RapidRAR.cr resolver"""

import re
from resources.lib.modules import control
from resources.lib.modules import client

RAPIDRAR_BASE = 'https://rapidrar.cr'

_session_cookie = None

def is_enabled():
    return control.setting('rapidrar.enabled') == 'true' and bool(control.setting('rapidrar.user'))

def _login():
    global _session_cookie
    if _session_cookie:
        return _session_cookie
    try:
        user = control.setting('rapidrar.user')
        passwd = control.setting('rapidrar.pass')
        if not user or not passwd:
            return None

        import requests
        s = requests.Session()
        s.headers.update({'User-Agent': control.USER_AGENT})

        # Try login
        login_url = RAPIDRAR_BASE + '/login'
        r = s.get(login_url, timeout=15)

        # Extract CSRF token if present
        csrf = ''
        try:
            csrf_match = re.search(r'name="csrf[_-]token"[^>]*value="([^"]+)"', r.text)
            if not csrf_match:
                csrf_match = re.search(r'name="_token"[^>]*value="([^"]+)"', r.text)
            if csrf_match:
                csrf = csrf_match.group(1)
        except:
            pass

        post_data = {'username': user, 'password': passwd}
        if csrf:
            post_data['_token'] = csrf

        login_r = s.post(login_url, data=post_data, timeout=15, allow_redirects=True)

        if login_r.ok and ('logout' in login_r.text.lower() or 'dashboard' in login_r.text.lower() or 'account' in login_r.text.lower()):
            _session_cookie = s.cookies.get_dict()
            control.log('RapidRAR login successful')
            return _session_cookie
        else:
            control.log('RapidRAR login failed')
            return None
    except Exception as e:
        control.log('RapidRAR login error: %s' % e)
        return None

def resolve(url):
    """Resolve a RapidRAR download link to a direct URL"""
    try:
        import requests
        s = requests.Session()
        s.headers.update({'User-Agent': control.USER_AGENT})

        cookies = _login()
        if cookies:
            s.cookies.update(cookies)

        # Get the download page
        r = s.get(url, timeout=15, allow_redirects=True)
        if not r.ok:
            return None

        # Look for direct download link
        direct = None

        # Pattern 1: Direct download button
        match = re.search(r'href="([^"]*(?:download|dl|get)[^"]*)"', r.text, re.I)
        if match:
            direct = match.group(1)

        # Pattern 2: File hosting pattern
        if not direct:
            match = re.search(r'(https?://[^"\']*rapidrar[^"\']*(?:\.mkv|\.mp4|\.avi|\.zip|\.rar))', r.text, re.I)
            if match:
                direct = match.group(1)

        # Pattern 3: Hidden form redirect
        if not direct:
            match = re.search(r'action="([^"]*)"[^>]*method="post"', r.text, re.I)
            if match:
                form_url = match.group(1)
                if not form_url.startswith('http'):
                    form_url = RAPIDRAR_BASE + form_url
                # Extract form fields
                fields = {}
                for fm in re.finditer(r'name="([^"]*)"[^>]*value="([^"]*)"', r.text):
                    fields[fm.group(1)] = fm.group(2)
                fr = s.post(form_url, data=fields, timeout=15, allow_redirects=True)
                if fr.ok:
                    direct = fr.url

        if direct:
            if not direct.startswith('http'):
                direct = RAPIDRAR_BASE + direct
            return direct

        return None
    except Exception as e:
        control.log('RapidRAR resolve error: %s' % e)
        return None
