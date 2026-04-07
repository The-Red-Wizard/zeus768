# -*- coding: utf-8 -*-
"""Syncher - simple file-based cache"""

import os
import json
import time
import hashlib
from resources.lib.modules import control

_CACHE_DIR = None

def _cache_dir():
    global _CACHE_DIR
    if _CACHE_DIR is None:
        _CACHE_DIR = os.path.join(control.addonProfile(), 'cache')
        os.makedirs(_CACHE_DIR, exist_ok=True)
    return _CACHE_DIR

def _key(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def get(url, hours=24):
    try:
        path = os.path.join(_cache_dir(), _key(url) + '.json')
        if not os.path.exists(path):
            return None
        mtime = os.path.getmtime(path)
        if time.time() - mtime > hours * 3600:
            return None
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return None

def set(url, data, hours=24):
    try:
        path = os.path.join(_cache_dir(), _key(url) + '.json')
        with open(path, 'w') as f:
            json.dump(data, f)
    except:
        pass

def clear():
    try:
        d = _cache_dir()
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
    except:
        pass
