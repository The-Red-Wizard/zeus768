# -*- coding: utf-8 -*-
"""
Poseidon Player - IPTV Manager Integration
Author: poseidon12
Provides channels and EPG data to IPTV Manager for full TV Guide
"""

import json
import socket
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()

def log(message, level=xbmc.LOGINFO):
    xbmc.log(f"[plugin.video.poseidonplayer.iptv] {message}", level)

class IPTVManager:
    """Interface to IPTV Manager"""

    def __init__(self, port):
        """Initialize IPTV Manager on the given port"""
        self.port = port

    def via_socket(func):
        """Send the output of the function through a socket"""
        def wrapper(self, *args, **kwargs):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', self.port))
            try:
                result = func(self, *args, **kwargs)
                sock.sendall(json.dumps(result).encode())
            finally:
                sock.close()
        return wrapper

    @via_socket
    def send_channels(self):
        """Return JSON-M3U formatted information to IPTV Manager"""
        from resources.lib.iptv_data import get_channels
        return get_channels()

    @via_socket
    def send_epg(self):
        """Return JSONTV formatted information to IPTV Manager"""
        from resources.lib.iptv_data import get_epg
        return get_epg()


def run(args):
    """Run the IPTV Manager integration"""
    if len(args) <= 1:
        return

    port = int(args[1])
    
    if len(args) > 2:
        if args[2] == 'channels':
            IPTVManager(port).send_channels()
        elif args[2] == 'epg':
            IPTVManager(port).send_epg()


if __name__ == '__main__':
    import sys
    run(sys.argv)
