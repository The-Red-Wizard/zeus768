# -*- coding: utf-8 -*-
"""Stigstream.ru source resolver.

Stigstream serves its source list via a doubly-encrypted JSON envelope:
  outer: AES-256-GCM
  inner: ChaCha20-Poly1305
both keyed via HKDF-SHA512 from a 32-byte master key embedded in the site's
JS bundle (``dd5473f09b62f07a.js`` as of v1.4.14).

After decryption, the API returns a list of HLS streams that point at the
site's CORS proxy ``proxy.stigstream.ru/m3u8-only-proxy`` — those URLs are
directly playable in any HLS-capable player (Kodi's built-in HLS, ExoPlayer,
etc.) so no further resolution is needed.

Endpoints used:
  GET  https://api.stigstream.ru/servers          -> list of {name, status, ...}
  GET  https://api.stigstream.ru/movie/{srv}/{tmdb}
  GET  https://api.stigstream.ru/tv/{srv}/{tmdb}/{season}/{episode}

Crypto library lookup order:
  1. pycryptodome (``Crypto.Cipher.AES`` + ``Crypto.Cipher.ChaCha20_Poly1305``)
     — common Kodi dependency, used by ResolveURL.
  2. ``cryptography`` (Python's pyca/cryptography) — sometimes present on
     desktop installs.
If neither is available, the resolver disables itself gracefully.
"""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from .common import log

API = 'https://api.stigstream.ru'
SITE = 'https://stigstream.ru'
TIMEOUT = 12

# 32-byte HKDF master key — extracted from the public JS bundle.
_MASTER_KEY_HEX = 'bc2145160a5085ba4d540f8fdc0db73ffcd71827b894988919633491bd77b797'
_AES_INFO = b'aes-256-gcm-layer-2'
_CC_INFO = b'chacha20-poly1305-layer-1'

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# Default servers to try (in priority order) if the /servers endpoint can't
# be reached. The actual list returned by the API is preferred.
_FALLBACK_SERVERS = ('Aqua', 'Nova', 'Vix', 'Nebula', 'Quartz',
                     'Obsidian', 'Onyx', 'Atlas')

# ---------------------------------------------------------------------------
# Crypto bootstrap
# ---------------------------------------------------------------------------

_keys_cache = None  # (aes_key, chacha_key) once derived


def _hkdf_sha512(ikm, info, length=32):
    """Pure stdlib HKDF-SHA512 (RFC 5869)."""
    import hmac
    import hashlib
    h = hashlib.sha512
    salt = b'\x00' * h().digest_size
    prk = hmac.new(salt, ikm, h).digest()
    out = b''
    t = b''
    counter = 1
    while len(out) < length:
        t = hmac.new(prk, t + info + bytes([counter]), h).digest()
        out += t
        counter += 1
    return out[:length]


def _derive_keys():
    global _keys_cache
    if _keys_cache:
        return _keys_cache
    master = bytes.fromhex(_MASTER_KEY_HEX)
    aes = _hkdf_sha512(master, _AES_INFO, 32)
    cc = _hkdf_sha512(master, _CC_INFO, 32)
    _keys_cache = (aes, cc)
    return _keys_cache


def _aesgcm_decrypt(key, iv, ciphertext, tag):
    """AES-256-GCM decrypt — tries pycryptodome first, then pyca/cryptography,
    then a pure-Python implementation embedded in this addon (slow but works
    on Kodi-Android where neither C library is available)."""
    try:
        from Crypto.Cipher import AES  # pycryptodome
        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        return cipher.decrypt_and_verify(ciphertext, tag)
    except ImportError:
        pass
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        return AESGCM(key).decrypt(iv, ciphertext + tag, None)
    except ImportError:
        pass
    from . import purecrypto
    return purecrypto.aes256_gcm_decrypt(key, iv, ciphertext, tag)


def _chacha_decrypt(key, iv, ciphertext, tag):
    """ChaCha20-Poly1305 decrypt — same library order as AES-GCM, with a
    pure-Python fallback."""
    try:
        from Crypto.Cipher import ChaCha20_Poly1305  # pycryptodome
        cipher = ChaCha20_Poly1305.new(key=key, nonce=iv)
        return cipher.decrypt_and_verify(ciphertext, tag)
    except ImportError:
        pass
    try:
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        return ChaCha20Poly1305(key).decrypt(iv, ciphertext + tag, None)
    except ImportError:
        pass
    from . import purecrypto
    return purecrypto.chacha20_poly1305_decrypt(key, iv, ciphertext, tag)


def _is_available():
    """Stigstream is now ALWAYS available — pure-Python crypto fallback ships
    with the addon (resources/lib/purecrypto.py)."""
    return True


def _decrypt_envelope(env):
    """Walk the two-layer envelope and return the final decrypted JSON dict."""
    if not env or env.get('v') != '2':
        raise ValueError('Stigstream: unexpected envelope version: %r' % env.get('v'))
    aes_key, chacha_key = _derive_keys()
    outer_iv = bytes.fromhex(env['aesIv'])
    outer_tag = bytes.fromhex(env['aesMac'])
    outer_ct = bytes.fromhex(env['inner'])
    outer = _aesgcm_decrypt(aes_key, outer_iv, outer_ct, outer_tag)
    inner = json.loads(outer)
    cc_iv = bytes.fromhex(inner['ccIv'])
    cc_tag = bytes.fromhex(inner['ccMac'])
    cc_ct = bytes.fromhex(inner['data'])
    payload = _chacha_decrypt(chacha_key, cc_iv, cc_ct, cc_tag)
    return json.loads(payload)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': UA,
        'Accept': 'application/json',
        'Accept-Language': 'en-GB,en;q=0.9',
        # Same brotli avoidance as the rest of the addon — Kodi-Python on
        # Android has no brotli decoder bundled.
        'Accept-Encoding': 'gzip, deflate',
        'Origin': SITE,
        'Referer': SITE + '/',
    })
    return s


def _api_get(sess, url):
    try:
        r = sess.get(url, timeout=TIMEOUT)
    except Exception as e:
        log('stigstream: GET %s failed: %s' % (url, e))
        return None
    if r.status_code != 200:
        log('stigstream: GET %s -> %s' % (url, r.status_code))
        return None
    try:
        env = r.json()
    except ValueError:
        log('stigstream: GET %s -> non-JSON body (len=%d)' % (url, len(r.text)))
        return None
    try:
        return _decrypt_envelope(env)
    except Exception as e:
        log('stigstream: decrypt %s failed: %s' % (url, e))
        return None


def list_servers(sess=None):
    sess = sess or _session()
    data = _api_get(sess, API + '/servers') or []
    if isinstance(data, dict):
        data = data.get('servers') or data.get('data') or []
    return [s for s in data if isinstance(s, dict) and s.get('status') == 'Working']


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_streams(media_type, tmdb_id, season=None, episode=None):
    """Return a list of stream dicts (compatible with the addon's player code).

    media_type: 'movie' | 'tv'
    """
    if not _is_available():
        log('stigstream: skipping — neither pycryptodome nor cryptography is '
            'importable in this Python environment.')
        return []
    if not tmdb_id:
        log('stigstream: tmdb_id is required (IMDb-only is not supported)')
        return []

    sess = _session()
    servers = list_servers(sess) or [
        {'name': n, 'description': ''} for n in _FALLBACK_SERVERS
    ]
    log('stigstream: %d candidate servers' % len(servers))

    if media_type == 'movie':
        path_tmpl = '/movie/{srv}/{tmdb}'
    else:
        path_tmpl = '/tv/{srv}/{tmdb}/{s}/{e}'

    streams = []

    def _fetch(srv):
        name = srv.get('name')
        url = API + path_tmpl.format(srv=name, tmdb=tmdb_id,
                                     s=season or 1, e=episode or 1)
        data = _api_get(sess, url)
        if not data:
            return []
        out = []
        for st in (data.get('streams') or []):
            su = st.get('url')
            if not su:
                continue
            label_bits = ['HLS', name]
            if srv.get('description'):
                label_bits.append(srv['description'])
            out.append({
                'url': su,
                'headers': {'User-Agent': UA, 'Referer': SITE + '/'},
                'label': '[%s] Stigstream • %s (%s)' % (
                    st.get('quality') or 'Auto', name,
                    srv.get('description') or ''),
                'quality': st.get('quality') or 'Auto',
                'proto': 'HLS', 'host': 'stigstream.ru',
                'server': 'Stigstream %s' % name,
                'height': 0, 'bandwidth': 0,
                'provider': 'stigstream',
                'subtitles': data.get('subtitles') or [],
            })
        return out

    # Servers respond fast; fan them out in parallel for snappy multi-server
    # source lists.
    with ThreadPoolExecutor(max_workers=min(8, len(servers))) as ex:
        futs = [ex.submit(_fetch, s) for s in servers]
        for f in as_completed(futs, timeout=30):
            try:
                streams.extend(f.result(timeout=1) or [])
            except Exception as e:
                log('stigstream: server fetch error: %s' % e)
    log('stigstream: resolved %d streams across %d servers'
        % (len(streams), len(servers)))
    return streams
