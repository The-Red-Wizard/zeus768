# -*- coding: utf-8 -*-
"""
QR Code Helper for Orion
Shows QR codes using Kodi's built-in picture viewer for universal skin compatibility
"""

import xbmc
import xbmcgui
import xbmcvfs
import urllib.request
import urllib.parse
import os
import ssl


def show_qr(service_name, url):
    """Download QR code and show with Kodi's built-in picture viewer"""
    encoded_data = urllib.parse.quote(url)
    qr_api = f'https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={encoded_data}&bgcolor=0-0-0&color=255-255-255'
    
    temp_path = xbmcvfs.translatePath('special://temp/')
    qr_file = os.path.join(temp_path, f'orion_qr_{service_name.lower().replace(" ", "_")}.png')
    
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(qr_api, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            with open(qr_file, 'wb') as f:
                f.write(resp.read())
    except Exception:
        qr_file = None
    
    if qr_file and os.path.exists(qr_file):
        # Show QR image fullscreen using Kodi's built-in picture viewer
        xbmc.executebuiltin(f'ShowPicture({qr_file})')
        xbmc.sleep(500)
        xbmcgui.Dialog().ok(
            f'{service_name} - QR Code',
            f'Scan the QR code behind this dialog, or visit:\n'
            f'[COLOR cyan]{url}[/COLOR]\n\n'
            f'Press OK then BACK to close the QR image.'
        )
        xbmc.executebuiltin('Action(Back)')
    else:
        xbmcgui.Dialog().ok(
            f'{service_name} Authorization',
            f'Visit: [COLOR cyan]{url}[/COLOR]\n\n'
            'Scan the QR code or visit the URL above to authorize.'
        )
