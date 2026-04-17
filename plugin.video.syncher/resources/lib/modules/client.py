# -*- coding: utf-8 -*-
"""Syncher - HTTP client with session management"""

import requests
import json
from resources.lib.modules import control

_session = None

def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({'User-Agent': control.USER_AGENT})
    return _session

def request(url, post=None, headers=None, timeout=15, json_resp=False):
    try:
        s = _get_session()
        if headers:
            h = dict(s.headers)
            h.update(headers)
        else:
            h = s.headers

        if post:
            if isinstance(post, str):
                r = s.post(url, data=post, headers=h, timeout=timeout, verify=True)
            else:
                r = s.post(url, json=post, headers=h, timeout=timeout, verify=True)
        else:
            r = s.get(url, headers=h, timeout=timeout, verify=True)

        r.raise_for_status()

        if json_resp:
            return r.json()
        return r.text
    except Exception as e:
        control.log('HTTP Error [%s]: %s' % (url[:60], e))
        return None

def request_json(url, post=None, headers=None, timeout=15):
    return request(url, post=post, headers=headers, timeout=timeout, json_resp=True)
