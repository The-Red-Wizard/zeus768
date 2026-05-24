"""
SALTS - iDrive account integration.

Two authentication modes are supported and configured via the Kodi setting
``idrive_mode``:

    * ``webdav`` - iDriveSync (idrivesync.com) and any other WebDAV-compatible
      iDrive endpoint.  Uses HTTP Basic auth + PROPFIND for listing and
      direct GET with Basic auth for streaming.

    * ``s3`` - iDrive e2 (S3-compatible object storage).  Uses access key /
      secret + AWS SigV4 signing to list objects and to generate presigned
      URLs that Kodi can stream directly.

The module exposes the standard cloud-provider interface consumed by
``cloud_library.py``:

    is_authed(), list_all_videos(progress_cb=None),
    get_stream_url(file_id), get_share_url(file_id)

``file_id`` here is the URL-safe object path returned in the listing.
"""
import base64
import datetime
import hashlib
import hmac
import os
import re
import urllib.parse
from urllib.request import Request, urlopen

import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()

VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm', '.ts',
             '.flv', '.wmv', '.mpg', '.mpeg', '.m2ts')


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _mode():
    return (ADDON.getSetting('idrive_mode') or 'webdav').strip().lower()


def _is_video(name):
    return name.lower().endswith(VIDEO_EXT)


def _log(msg, level=None):
    try:
        xbmc.log(f'cloud_idrive: {msg}',
                 level if level is not None else xbmc.LOGDEBUG)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# WebDAV mode
# ---------------------------------------------------------------------------

_WEBDAV_DEFAULT_URL = 'https://www.idrivesync.com/webdav'


def _webdav_conf():
    url = (ADDON.getSetting('idrive_webdav_url') or _WEBDAV_DEFAULT_URL).strip()
    if not url.endswith('/'):
        url += '/'
    user = (ADDON.getSetting('idrive_webdav_user') or '').strip()
    pw = ADDON.getSetting('idrive_webdav_pass') or ''
    return url, user, pw


def _webdav_auth_header(user, pw):
    token = base64.b64encode(f'{user}:{pw}'.encode('utf-8')).decode('ascii')
    return f'Basic {token}'


def _webdav_authed():
    url, user, pw = _webdav_conf()
    return bool(url and user and pw)


def _webdav_request(method, url, user, pw, depth=None, body=None, timeout=20):
    headers = {
        'Authorization': _webdav_auth_header(user, pw),
        'User-Agent': 'SALTS/iDrive',
    }
    if depth is not None:
        headers['Depth'] = str(depth)
    if body is not None:
        headers['Content-Type'] = 'application/xml; charset=utf-8'
        body = body.encode('utf-8')
    req = Request(url, data=body, headers=headers, method=method)
    return urlopen(req, timeout=timeout)


_PROPFIND_BODY = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<d:propfind xmlns:d="DAV:">'
    '<d:prop>'
    '<d:displayname/><d:getcontentlength/><d:resourcetype/>'
    '<d:getcontenttype/><d:getlastmodified/>'
    '</d:prop>'
    '</d:propfind>'
)

_RESP_RE = re.compile(
    r'<(?:[a-zA-Z0-9]+:)?response[^>]*>(.*?)</(?:[a-zA-Z0-9]+:)?response>',
    re.S | re.I)
_HREF_RE = re.compile(
    r'<(?:[a-zA-Z0-9]+:)?href[^>]*>(.*?)</(?:[a-zA-Z0-9]+:)?href>', re.S | re.I)
_LEN_RE = re.compile(
    r'<(?:[a-zA-Z0-9]+:)?getcontentlength[^>]*>(\d+)</', re.I)
_COLL_RE = re.compile(
    r'<(?:[a-zA-Z0-9]+:)?collection\s*/>', re.I)
_MIME_RE = re.compile(
    r'<(?:[a-zA-Z0-9]+:)?getcontenttype[^>]*>(.*?)</', re.I)


def _webdav_walk(base_url, user, pw, progress_cb=None):
    """Walk WebDAV starting from base_url (a directory).  Yields dicts with
    keys: id, name, size, mimeType, modifiedTime."""
    base_parsed = urllib.parse.urlsplit(base_url)
    base_path = base_parsed.path
    # stack of directory URLs (absolute) still to visit
    stack = [base_url]
    seen = set()
    found = 0
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        try:
            resp = _webdav_request('PROPFIND', cur, user, pw, depth=1,
                                   body=_PROPFIND_BODY, timeout=30)
            xml = resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            _log(f'webdav PROPFIND {cur}: {e}', xbmc.LOGWARNING)
            continue
        for block in _RESP_RE.findall(xml):
            mh = _HREF_RE.search(block)
            if not mh:
                continue
            href = mh.group(1).strip()
            href = urllib.parse.unquote(href)
            # Build absolute URL for the resource
            if href.startswith('http://') or href.startswith('https://'):
                abs_url = href
                resource_path = urllib.parse.urlsplit(href).path
            else:
                abs_url = urllib.parse.urljoin(
                    f'{base_parsed.scheme}://{base_parsed.netloc}',
                    urllib.parse.quote(href))
                resource_path = href
            # Skip the directory itself
            cur_path = urllib.parse.urlsplit(cur).path
            if resource_path.rstrip('/') == cur_path.rstrip('/'):
                continue
            is_dir = bool(_COLL_RE.search(block))
            if is_dir:
                if not abs_url.endswith('/'):
                    abs_url += '/'
                stack.append(abs_url)
                continue
            name = resource_path.rstrip('/').rsplit('/', 1)[-1]
            if not _is_video(name):
                continue
            size = 0
            ml = _LEN_RE.search(block)
            if ml:
                try:
                    size = int(ml.group(1))
                except Exception:
                    size = 0
            mt = ''
            mm = _MIME_RE.search(block)
            if mm:
                mt = mm.group(1).strip()
            # file_id = path relative to base, url-quoted
            rel_path = resource_path
            if rel_path.startswith(base_path):
                rel_path = rel_path[len(base_path):]
            rel_path = rel_path.lstrip('/')
            found += 1
            if progress_cb:
                try:
                    progress_cb(found, found)
                except Exception:
                    pass
            yield {
                'id': urllib.parse.quote(rel_path, safe='/'),
                'name': name,
                'size': size,
                'mimeType': mt or 'video/mp4',
                'modifiedTime': '',
            }


def _webdav_list_all(progress_cb=None):
    url, user, pw = _webdav_conf()
    return list(_webdav_walk(url, user, pw, progress_cb=progress_cb))


def _webdav_stream_url(file_id):
    """Embed Basic auth into the URL so Kodi's player can fetch directly."""
    url, user, pw = _webdav_conf()
    full = urllib.parse.urljoin(url, file_id)
    parsed = urllib.parse.urlsplit(full)
    u = urllib.parse.quote(user, safe='')
    p = urllib.parse.quote(pw, safe='')
    netloc = f'{u}:{p}@{parsed.netloc}'
    return urllib.parse.urlunsplit(
        (parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


# ---------------------------------------------------------------------------
# S3 (iDrive e2) mode
# ---------------------------------------------------------------------------

def _s3_conf():
    return {
        'key': (ADDON.getSetting('idrive_s3_key') or '').strip(),
        'secret': (ADDON.getSetting('idrive_s3_secret') or '').strip(),
        'endpoint': (ADDON.getSetting('idrive_s3_endpoint') or '').strip(),
        'bucket': (ADDON.getSetting('idrive_s3_bucket') or '').strip(),
        'region': (ADDON.getSetting('idrive_s3_region') or 'us-east-1').strip(),
        'prefix': (ADDON.getSetting('idrive_s3_prefix') or '').strip(),
    }


def _s3_authed():
    c = _s3_conf()
    return bool(c['key'] and c['secret'] and c['endpoint'] and c['bucket'])


def _sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def _hmac(key, msg, hex_out=False):
    h = hmac.new(key, msg.encode('utf-8'), hashlib.sha256)
    return h.hexdigest() if hex_out else h.digest()


def _s3_signing_key(secret, date_stamp, region, service='s3'):
    k = ('AWS4' + secret).encode('utf-8')
    k = _hmac(k, date_stamp)
    k = _hmac(k, region)
    k = _hmac(k, service)
    return _hmac(k, 'aws4_request')


def _s3_host_from_endpoint(endpoint):
    p = urllib.parse.urlsplit(endpoint if '://' in endpoint
                              else f'https://{endpoint}')
    return p.scheme or 'https', p.netloc or p.path


def _s3_signed_request(method, path, query, headers, payload=b''):
    """Sign and execute an S3 request, returning the response body bytes."""
    c = _s3_conf()
    scheme, host = _s3_host_from_endpoint(c['endpoint'])
    region = c['region']
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = now.strftime('%Y%m%d')

    canonical_uri = '/' + path.lstrip('/')
    canonical_uri = urllib.parse.quote(canonical_uri, safe='/')

    qpairs = sorted(query.items())
    canonical_qs = '&'.join(
        f'{urllib.parse.quote(k, safe="")}={urllib.parse.quote(str(v), safe="")}'
        for k, v in qpairs)

    payload_hash = _sha256_hex(payload)
    hdrs = {
        'host': host,
        'x-amz-content-sha256': payload_hash,
        'x-amz-date': amz_date,
    }
    hdrs.update({k.lower(): v for k, v in (headers or {}).items()})
    signed_headers = ';'.join(sorted(hdrs.keys()))
    canonical_headers = ''.join(
        f'{k}:{hdrs[k].strip()}\n' for k in sorted(hdrs.keys()))

    canonical_request = '\n'.join([
        method.upper(),
        canonical_uri,
        canonical_qs,
        canonical_headers,
        signed_headers,
        payload_hash,
    ])

    credential_scope = f'{date_stamp}/{region}/s3/aws4_request'
    string_to_sign = '\n'.join([
        'AWS4-HMAC-SHA256',
        amz_date,
        credential_scope,
        _sha256_hex(canonical_request.encode('utf-8')),
    ])

    signing_key = _s3_signing_key(c['secret'], date_stamp, region)
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'),
                         hashlib.sha256).hexdigest()
    auth = (f'AWS4-HMAC-SHA256 Credential={c["key"]}/{credential_scope}, '
            f'SignedHeaders={signed_headers}, Signature={signature}')

    url = f'{scheme}://{host}{canonical_uri}'
    if canonical_qs:
        url += '?' + canonical_qs
    req_headers = dict(hdrs)
    req_headers['Authorization'] = auth
    req = Request(url, data=payload or None,
                  headers={k: v for k, v in req_headers.items()
                           if k.lower() != 'host'},
                  method=method.upper())
    with urlopen(req, timeout=30) as resp:
        return resp.read()


def _s3_list_objects(progress_cb=None):
    c = _s3_conf()
    bucket = c['bucket']
    prefix = c['prefix'].lstrip('/')
    cont_token = None
    found = 0
    out = []
    # Iterate paginated ListObjectsV2
    while True:
        query = {
            'list-type': '2',
            'max-keys': '1000',
        }
        if prefix:
            query['prefix'] = prefix
        if cont_token:
            query['continuation-token'] = cont_token
        try:
            body = _s3_signed_request(
                'GET', f'/{bucket}', query, headers=None)
        except Exception as e:
            _log(f's3 list error: {e}', xbmc.LOGWARNING)
            break
        text = body.decode('utf-8', errors='ignore')
        # Crude XML parsing - we only need a few fields
        keys = re.findall(r'<Key>([^<]+)</Key>', text)
        sizes = re.findall(r'<Size>(\d+)</Size>', text)
        for i, k in enumerate(keys):
            if not _is_video(k):
                continue
            name = k.rsplit('/', 1)[-1]
            size = 0
            if i < len(sizes):
                try:
                    size = int(sizes[i])
                except Exception:
                    size = 0
            found += 1
            out.append({
                'id': k,  # full object key
                'name': name,
                'size': size,
                'mimeType': 'video/mp4',
                'modifiedTime': '',
            })
            if progress_cb and found % 25 == 0:
                try:
                    progress_cb(found, found)
                except Exception:
                    pass
        truncated = '<IsTruncated>true</IsTruncated>' in text
        if not truncated:
            break
        m = re.search(r'<NextContinuationToken>([^<]+)</NextContinuationToken>',
                      text)
        if not m:
            break
        cont_token = m.group(1)
    if progress_cb:
        try:
            progress_cb(found, found)
        except Exception:
            pass
    return out


def _s3_presigned_url(object_key, expires=3600):
    """Generate an S3 presigned GET URL valid for `expires` seconds."""
    c = _s3_conf()
    scheme, host = _s3_host_from_endpoint(c['endpoint'])
    region = c['region']
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = now.strftime('%Y%m%d')
    credential_scope = f'{date_stamp}/{region}/s3/aws4_request'

    canonical_uri = (f'/{c["bucket"]}/'
                     + urllib.parse.quote(object_key, safe='/'))

    query = {
        'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
        'X-Amz-Credential': f'{c["key"]}/{credential_scope}',
        'X-Amz-Date': amz_date,
        'X-Amz-Expires': str(int(expires)),
        'X-Amz-SignedHeaders': 'host',
    }
    canonical_qs = '&'.join(
        f'{urllib.parse.quote(k, safe="")}={urllib.parse.quote(v, safe="")}'
        for k, v in sorted(query.items()))

    canonical_headers = f'host:{host}\n'
    signed_headers = 'host'
    payload_hash = 'UNSIGNED-PAYLOAD'
    canonical_request = '\n'.join([
        'GET',
        canonical_uri,
        canonical_qs,
        canonical_headers,
        signed_headers,
        payload_hash,
    ])
    string_to_sign = '\n'.join([
        'AWS4-HMAC-SHA256',
        amz_date,
        credential_scope,
        _sha256_hex(canonical_request.encode('utf-8')),
    ])
    signing_key = _s3_signing_key(c['secret'], date_stamp, region)
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'),
                         hashlib.sha256).hexdigest()
    return (f'{scheme}://{host}{canonical_uri}?{canonical_qs}'
            f'&X-Amz-Signature={signature}')


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def is_authed():
    m = _mode()
    if m == 's3':
        return _s3_authed()
    return _webdav_authed()


def list_all_videos(progress_cb=None):
    m = _mode()
    if m == 's3':
        return _s3_list_objects(progress_cb=progress_cb)
    return _webdav_list_all(progress_cb=progress_cb)


def get_stream_url(file_id):
    if not file_id:
        return None
    m = _mode()
    if m == 's3':
        return _s3_presigned_url(file_id)
    return _webdav_stream_url(file_id)


def get_share_url(file_id):
    # For direct-play providers we just hand back the stream URL.
    return get_stream_url(file_id)


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def test_connection():
    """Light end-to-end test, surfaced from settings."""
    import xbmcgui
    name = 'iDrive'
    icon = ADDON.getAddonInfo('icon')
    if not is_authed():
        xbmcgui.Dialog().notification(
            name, 'Not configured - fill in credentials first', icon)
        return
    m = _mode()
    try:
        if m == 's3':
            # HEAD-equivalent: list with max-keys=1
            c = _s3_conf()
            _s3_signed_request('GET', f'/{c["bucket"]}',
                               {'list-type': '2', 'max-keys': '1'}, None)
        else:
            url, user, pw = _webdav_conf()
            _webdav_request('PROPFIND', url, user, pw, depth=0,
                            body=_PROPFIND_BODY, timeout=15)
        xbmcgui.Dialog().notification(name, f'{m.upper()} OK', icon)
    except Exception as e:
        xbmcgui.Dialog().ok(name, f'{m.upper()} connection failed:\n{e}')


def logout():
    """Clear all iDrive account credentials."""
    for k in ('idrive_webdav_user', 'idrive_webdav_pass',
              'idrive_s3_key', 'idrive_s3_secret', 'idrive_s3_bucket',
              'idrive_s3_prefix'):
        try:
            ADDON.setSetting(k, '')
        except Exception:
            pass
    import xbmcgui
    xbmcgui.Dialog().notification(
        'iDrive', 'Account credentials cleared', ADDON.getAddonInfo('icon'))
