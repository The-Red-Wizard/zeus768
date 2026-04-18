"""
SALTS Library - Logging utilities
Revived by zeus768 for Kodi 21+
"""
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ID = ADDON.getAddonInfo('id')

def log(msg, level=xbmc.LOGDEBUG):
    """Log a message to Kodi log"""
    try:
        if isinstance(msg, bytes):
            msg = msg.decode('utf-8', 'replace')
        message = f'{ADDON_NAME}: {msg}'
        xbmc.log(message, level)
    except Exception as e:
        xbmc.log(f'{ADDON_NAME}: Logging error: {e}', xbmc.LOGERROR)

def log_debug(msg):
    """Log debug message"""
    log(msg, xbmc.LOGDEBUG)

def log_info(msg):
    """Log info message"""
    log(msg, xbmc.LOGINFO)

def log_warning(msg):
    """Log warning message"""
    log(msg, xbmc.LOGWARNING)

def log_error(msg):
    """Log error message"""
    log(msg, xbmc.LOGERROR)
