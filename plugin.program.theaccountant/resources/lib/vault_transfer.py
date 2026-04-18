"""
The Accountant - Vault Transfer (QR Export / Import)
Encrypt vault with user passphrase, upload to GoFile, show QR of the URL.
On a new device: enter URL + passphrase to restore the vault.

Crypto: HMAC-SHA256 counter-mode stream cipher + PBKDF2 key derivation.
Not AES but strong enough for private family-device migration - and uses
only stdlib so it runs on every Kodi Python environment.
"""
import os
import json
import hmac
import base64
import hashlib
import zlib
import urllib.request
import urllib.parse
import ssl

import xbmc

MAGIC = b'ACNT1'  # format marker so import can validate
PBKDF2_ITERS = 120_000
SALT_LEN = 16
IV_LEN = 16
MAC_LEN = 32


def _derive_key(passphrase, salt):
    return hashlib.pbkdf2_hmac('sha256', passphrase.encode('utf-8'), salt, PBKDF2_ITERS, dklen=32)


def _keystream(key, iv, length):
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hashlib.sha256(key + iv + counter.to_bytes(8, 'big')).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def encrypt_blob(plaintext, passphrase):
    """Return url-safe base64 ciphertext: magic|salt|iv|ct|mac."""
    salt = os.urandom(SALT_LEN)
    iv = os.urandom(IV_LEN)
    key = _derive_key(passphrase, salt)
    ks = _keystream(key, iv, len(plaintext))
    ct = bytes(a ^ b for a, b in zip(plaintext, ks))
    mac = hmac.new(key, MAGIC + salt + iv + ct, hashlib.sha256).digest()
    raw = MAGIC + salt + iv + ct + mac
    return base64.urlsafe_b64encode(raw).decode('ascii')


def decrypt_blob(b64_ciphertext, passphrase):
    raw = base64.urlsafe_b64decode(b64_ciphertext.encode('ascii'))
    if not raw.startswith(MAGIC):
        raise ValueError('Invalid format: missing magic header')
    body = raw[len(MAGIC):]
    salt, iv = body[:SALT_LEN], body[SALT_LEN:SALT_LEN + IV_LEN]
    mac = body[-MAC_LEN:]
    ct = body[SALT_LEN + IV_LEN:-MAC_LEN]
    key = _derive_key(passphrase, salt)
    expected = hmac.new(key, MAGIC + salt + iv + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError('Wrong passphrase or corrupted payload')
    ks = _keystream(key, iv, len(ct))
    return bytes(a ^ b for a, b in zip(ct, ks))


def _http(url, method='GET', data=None, headers=None, timeout=30):
    hdrs = headers or {}
    hdrs.setdefault('User-Agent', 'Mozilla/5.0 TheAccountant/4.2')
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return resp.read()


LITTERBOX_URL = 'https://litterbox.catbox.moe/resources/internals/api.php'


def upload_encrypted(data_bytes, filename='vault.acnt', retention='72h'):
    """Upload bytes to Litterbox (temporary file host) and return the direct URL.

    Litterbox is a free, no-auth temporary file host (24h/12h/1h/72h retention)
    run by catbox.moe. Returns a plain-text direct URL on success.
    """
    boundary = '----acnt' + base64.urlsafe_b64encode(os.urandom(8)).decode('ascii').rstrip('=')
    parts = []
    for name, val in (('reqtype', 'fileupload'), ('time', retention)):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{val}\r\n'.encode('utf-8'))
    parts.append((
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="fileToUpload"; filename="{filename}"\r\n'
        'Content-Type: application/octet-stream\r\n\r\n'
    ).encode('utf-8'))
    parts.append(data_bytes)
    parts.append(f'\r\n--{boundary}--\r\n'.encode('utf-8'))
    body = b''.join(parts)

    resp = _http(LITTERBOX_URL, method='POST', data=body, headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}'
    }, timeout=60)
    url = resp.decode('utf-8', errors='replace').strip()
    if not url.startswith('http'):
        raise RuntimeError(f'Upload failed: {url[:200]}')
    return url


def download_encrypted(url):
    """Fetch the raw encrypted blob bytes from a direct URL."""
    return _http(url, timeout=60)


def export_vault(vault, passphrase, retention='72h'):
    """Compress, encrypt, upload vault. Returns the shareable direct URL."""
    raw = json.dumps(vault, separators=(',', ':')).encode('utf-8')
    compressed = zlib.compress(raw, 9)
    ciphertext_b64 = encrypt_blob(compressed, passphrase)
    return upload_encrypted(ciphertext_b64.encode('ascii'), retention=retention)


def import_vault(url, passphrase):
    """Download + decrypt vault from direct URL. Returns dict."""
    blob = download_encrypted(url).decode('ascii', errors='replace').strip()
    compressed = decrypt_blob(blob, passphrase)
    raw = zlib.decompress(compressed)
    return json.loads(raw.decode('utf-8'))


def qr_image_url(data, size=400):
    """Return a URL to a PNG QR encoding the given data (via qrserver.com)."""
    return (
        f'https://api.qrserver.com/v1/create-qr-code/'
        f'?size={size}x{size}&bgcolor=0-0-0&color=255-255-255&margin=10'
        f'&data={urllib.parse.quote(data, safe="")}'
    )
