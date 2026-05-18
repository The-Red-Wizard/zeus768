"""Anonymous Gofile upload helper.

Implements the minimum needed to re-upload a remote URL (resolved through
TorBox) to Gofile.io. We use the public ``uploadFile`` endpoint without an
account token, which yields a guest-owned file.

Endpoints used (https://gofile.io/api):
  - GET  https://api.gofile.io/servers           -> pick a store server
  - POST https://{server}.gofile.io/contents/uploadfile

The plugin uploads via a streaming download->upload pipe so very large
files don't have to be staged on disk.
"""
from __future__ import annotations

import json
import mimetypes
import os
import time
import uuid
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

import xbmc
import xbmcgui
import xbmcvfs

USER_AGENT = 'TraktPlayer/2.4.12 (+gofile)'
GOFILE_API = 'https://api.gofile.io'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log(f'Gofile: {msg}', level)


def _http_json(url, timeout=30):
    req = Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8', errors='replace'))
    except (URLError, HTTPError) as e:
        _log(f'GET {url} failed: {e}', xbmc.LOGERROR)
    except Exception as e:
        _log(f'GET {url} unexpected error: {e}', xbmc.LOGERROR)
    return None


def _pick_server():
    """Ask Gofile which store server to use."""
    data = _http_json(f'{GOFILE_API}/servers')
    if not isinstance(data, dict) or data.get('status') != 'ok':
        return None
    servers = (data.get('data') or {}).get('servers') or []
    if not servers:
        return None
    # Prefer the first server (lowest load per Gofile docs)
    return servers[0].get('name')


def _filename_from_url(url, fallback='upload.bin'):
    try:
        path = urlparse(url).path
        name = os.path.basename(path) or fallback
        # Strip query/fragments accidentally retained
        return name.split('?')[0].split('#')[0] or fallback
    except Exception:
        return fallback


def _multipart_iter(boundary, filename, content_type, src_resp,
                    chunk_size=1024 * 1024, on_progress=None, total=None):
    """Yield multipart/form-data bytes streamed from ``src_resp``."""
    head = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f'Content-Type: {content_type}\r\n\r\n'
    ).encode('utf-8')
    yield head

    read = 0
    last_pct = -1
    while True:
        chunk = src_resp.read(chunk_size)
        if not chunk:
            break
        read += len(chunk)
        if on_progress and total:
            pct = int(read * 100 / total)
            if pct != last_pct:
                on_progress(pct, read, total)
                last_pct = pct
        yield chunk

    tail = f'\r\n--{boundary}--\r\n'.encode('utf-8')
    yield tail


class _ChunkedBody:
    """Wrap an iterator of byte chunks so urllib can use it as request data."""

    def __init__(self, iterator):
        self._it = iter(iterator)
        self._buf = b''

    def read(self, n=-1):
        if n is None or n < 0:
            return b''.join(list(self._it))
        while len(self._buf) < n:
            try:
                self._buf += next(self._it)
            except StopIteration:
                break
        out, self._buf = self._buf[:n], self._buf[n:]
        return out


def upload_remote_url(src_url, display_name=None, show_progress=True):
    """Stream-download from ``src_url`` and upload to Gofile.

    Returns the public download page URL on success, otherwise None.
    """
    if not src_url:
        return None

    server = _pick_server()
    if not server:
        _log('No Gofile server available', xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            'Gofile', 'Could not reach Gofile servers',
            xbmcgui.NOTIFICATION_ERROR
        )
        return None

    upload_url = f'https://{server}.gofile.io/contents/uploadfile'
    fname = display_name or _filename_from_url(src_url)
    ctype = mimetypes.guess_type(fname)[0] or 'application/octet-stream'

    _log(f'Uploading "{fname}" via {server}.gofile.io')

    dialog = None
    if show_progress:
        try:
            dialog = xbmcgui.DialogProgressBG()
            dialog.create('Gofile Upload', f'{fname} - starting...')
        except Exception:
            dialog = None

    def _progress(pct, read, total):
        if dialog is None:
            return
        try:
            mb = read / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            dialog.update(
                max(0, min(100, pct)),
                'Gofile Upload',
                f'{fname} - {mb:.1f}/{tot_mb:.1f} MB ({pct}%)'
            )
        except Exception:
            pass

    try:
        src_req = Request(src_url, headers={'User-Agent': USER_AGENT})
        src_resp = urlopen(src_req, timeout=60)
        total = 0
        try:
            total = int(src_resp.headers.get('Content-Length') or 0)
        except Exception:
            total = 0

        boundary = f'----TraktPlayerBoundary{uuid.uuid4().hex}'
        body_iter = _multipart_iter(
            boundary, fname, ctype, src_resp,
            on_progress=_progress, total=total,
        )

        # urllib only supports bytes for request body; ChunkedBody adapts
        # the iterator into a file-like .read() that urllib can consume.
        body = _ChunkedBody(body_iter)

        headers = {
            'User-Agent': USER_AGENT,
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Accept': 'application/json',
        }
        if total:
            # Pre-compute total request size so urllib can set Content-Length.
            head_len = len((
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="file"; filename="{fname}"\r\n'
                f'Content-Type: {ctype}\r\n\r\n'
            ).encode('utf-8'))
            tail_len = len(f'\r\n--{boundary}--\r\n'.encode('utf-8'))
            headers['Content-Length'] = str(head_len + total + tail_len)

        up_req = Request(upload_url, data=body, headers=headers, method='POST')
        with urlopen(up_req, timeout=None) as up_resp:
            raw = up_resp.read().decode('utf-8', errors='replace')

        try:
            payload = json.loads(raw)
        except Exception:
            _log(f'Non-JSON response: {raw[:200]}', xbmc.LOGERROR)
            return None

        if payload.get('status') != 'ok':
            _log(f'Upload failed: {payload}', xbmc.LOGERROR)
            return None

        data = payload.get('data') or {}
        page = (data.get('downloadPage') or data.get('directLink')
                or data.get('fileUrl') or '')
        _log(f'Upload OK -> {page}')
        return page
    except (URLError, HTTPError) as e:
        _log(f'Upload network error: {e}', xbmc.LOGERROR)
        return None
    except Exception as e:
        _log(f'Upload error: {e}', xbmc.LOGERROR)
        return None
    finally:
        if dialog is not None:
            try:
                dialog.close()
            except Exception:
                pass


def upload_and_notify(src_url, display_name=None, save_to_setting=True):
    """Upload then show a notification + ``OK`` dialog with the link.

    If ``save_to_setting`` is True, the resulting URL is also stored in the
    addon setting ``tb_gofile_last`` so the user can copy it later.
    """
    if not src_url:
        return None

    page = upload_remote_url(src_url, display_name=display_name)
    if not page:
        xbmcgui.Dialog().notification(
            'Gofile', 'Upload failed - see log',
            xbmcgui.NOTIFICATION_ERROR
        )
        return None

    if save_to_setting:
        try:
            import xbmcaddon
            xbmcaddon.Addon().setSetting('tb_gofile_last', page)
        except Exception:
            pass

    try:
        xbmcgui.Dialog().ok('Gofile Upload Complete',
                            f'Your link:\n[B]{page}[/B]\n\n'
                            f'(Also saved in Settings -> TorBox)')
    except Exception:
        xbmcgui.Dialog().notification(
            'Gofile', 'Upload complete',
            xbmcgui.NOTIFICATION_INFO, 6000
        )
    return page
