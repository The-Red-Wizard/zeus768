"""
The Accountant - Network Speed Test

Measures download throughput and basic latency to Cloudflare / Fast.com-style
endpoints. Uses only stdlib so it runs everywhere Kodi runs.
"""
import time
import ssl
import socket
import urllib.request
import urllib.parse

CF_DOWN = 'https://speed.cloudflare.com/__down?bytes={size}'
HETZNER_100MB = 'https://ash-speed.hetzner.com/100MB.bin'
SIZES = {
    'Quick (10 MB)': 10 * 1024 * 1024,
    'Normal (25 MB)': 25 * 1024 * 1024,
    'Thorough (100 MB)': 100 * 1024 * 1024,
}


def _ping(host, port=443, timeout=5):
    """Return TCP connect latency in ms, or None on failure."""
    try:
        start = time.time()
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return int((time.time() - start) * 1000)
    except Exception:
        return None


def _download(url, expected_bytes, progress_cb=None, timeout=60):
    """Stream-download a URL and return (bytes_read, seconds_elapsed)."""
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers={'User-Agent': 'TheAccountant/4.3'})
    start = time.time()
    read = 0
    chunk_size = 64 * 1024
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        while True:
            buf = resp.read(chunk_size)
            if not buf:
                break
            read += len(buf)
            if progress_cb is not None:
                try:
                    progress_cb(read, expected_bytes)
                except Exception:
                    pass
    return read, max(0.001, time.time() - start)


def run_speed_test(size_bytes=25 * 1024 * 1024, progress_cb=None):
    """Full speed test: ping + CF download + Hetzner fallback if needed.

    Returns dict:
      {
        'ping_ms':         int,
        'download_mbps':   float,
        'downloaded_mb':   float,
        'elapsed_s':       float,
        'endpoint':        str,
        'error':           str or None,
      }
    """
    result = {
        'ping_ms': None,
        'download_mbps': 0.0,
        'downloaded_mb': 0.0,
        'elapsed_s': 0.0,
        'endpoint': '',
        'error': None,
    }

    # 1. Ping (TCP connect to 1.1.1.1:443 - closest proxy for CF)
    result['ping_ms'] = _ping('1.1.1.1', 443)
    if result['ping_ms'] is None:
        result['ping_ms'] = _ping('speed.cloudflare.com', 443)

    # 2. Download test
    url = CF_DOWN.format(size=size_bytes)
    result['endpoint'] = url
    try:
        read, elapsed = _download(url, size_bytes, progress_cb=progress_cb, timeout=90)
    except Exception as e:
        # Fall back to Hetzner public 100MB test file
        try:
            result['endpoint'] = HETZNER_100MB
            read, elapsed = _download(HETZNER_100MB, 100 * 1024 * 1024,
                                       progress_cb=progress_cb, timeout=120)
        except Exception as e2:
            result['error'] = f'{type(e).__name__}: {e} | fallback: {e2}'
            return result

    mb = read / (1024 * 1024)
    mbps = (read * 8) / (elapsed * 1_000_000)  # megabits/sec
    result['download_mbps'] = round(mbps, 2)
    result['downloaded_mb'] = round(mb, 2)
    result['elapsed_s'] = round(elapsed, 2)
    return result


def format_result(result):
    """Pretty-print the speed test result for an OK dialog."""
    if result.get('error'):
        return f"Speed test failed:\n{result['error']}"
    ping = result.get('ping_ms')
    ping_str = f'{ping} ms' if ping is not None else 'n/a'
    speed = result.get('download_mbps', 0)
    # Friendly rating
    if speed >= 100:
        rating = 'Excellent - 4K ready'
    elif speed >= 40:
        rating = 'Good - 1080p streaming'
    elif speed >= 15:
        rating = 'OK - 720p streaming'
    elif speed >= 5:
        rating = 'Slow - SD streaming only'
    else:
        rating = 'Poor - buffering likely'
    lines = [
        f'Download: {speed} Mbps ({result["downloaded_mb"]} MB in {result["elapsed_s"]}s)',
        f'Latency:  {ping_str}',
        f'Rating:   {rating}',
        f'Endpoint: {result["endpoint"][:70]}',
    ]
    return '\n'.join(lines)
