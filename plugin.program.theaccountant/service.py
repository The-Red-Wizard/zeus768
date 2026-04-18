"""
The Accountant - Background Service
Checks debrid account expiry on Kodi startup and warns user.
"""
import xbmc, xbmcgui, xbmcaddon
import json, os, time

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = os.path.join(ADDON_PATH, 'icon.png')
VAULT_FILE = os.path.join(ADDON_PATH, 'vault.json')

WARNING_DAYS = 7  # Warn when less than 7 days left
CRITICAL_DAYS = 2  # Critical warning when less than 2 days


def load_vault():
    try:
        with open(VAULT_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def check_expiry():
    """Check all debrid accounts and warn if expiring soon"""
    vault = load_vault()
    warnings = []

    # Real-Debrid
    rd_token = vault.get('rd_token', '')
    if rd_token:
        try:
            from resources.lib.auth_manager import get_rd_account_info
            info = get_rd_account_info(rd_token)
            if info:
                days = info['days_left']
                if days <= 0:
                    warnings.append(('Real-Debrid', 'EXPIRED', 0))
                elif days <= CRITICAL_DAYS:
                    warnings.append(('Real-Debrid', 'EXPIRING', days))
                elif days <= WARNING_DAYS:
                    warnings.append(('Real-Debrid', 'WARNING', days))
        except:
            pass

    # Premiumize
    pm_token = vault.get('pm_token', '')
    if pm_token:
        try:
            from resources.lib.auth_manager import get_pm_account_info
            info = get_pm_account_info(pm_token)
            if info:
                days = info['days_left']
                if days <= 0:
                    warnings.append(('Premiumize', 'EXPIRED', 0))
                elif days <= CRITICAL_DAYS:
                    warnings.append(('Premiumize', 'EXPIRING', days))
                elif days <= WARNING_DAYS:
                    warnings.append(('Premiumize', 'WARNING', days))
        except:
            pass

    # AllDebrid
    ad_token = vault.get('ad_token', '')
    if ad_token:
        try:
            from resources.lib.auth_manager import get_ad_account_info
            info = get_ad_account_info(ad_token)
            if info:
                days = info['days_left']
                if days <= 0:
                    warnings.append(('AllDebrid', 'EXPIRED', 0))
                elif days <= CRITICAL_DAYS:
                    warnings.append(('AllDebrid', 'EXPIRING', days))
                elif days <= WARNING_DAYS:
                    warnings.append(('AllDebrid', 'WARNING', days))
        except:
            pass

    # Show warnings
    for service, level, days in warnings:
        if level == 'EXPIRED':
            xbmcgui.Dialog().notification(
                f'{service} EXPIRED',
                'Your subscription has expired! Renew now.',
                ADDON_ICON, 10000
            )
        elif level == 'EXPIRING':
            xbmcgui.Dialog().notification(
                f'{service} Expiring!',
                f'Only {days} day{"s" if days != 1 else ""} left! Renew soon.',
                ADDON_ICON, 8000
            )
        elif level == 'WARNING':
            xbmcgui.Dialog().notification(
                f'{service} Reminder',
                f'{days} days remaining on your subscription.',
                ADDON_ICON, 5000
            )
        # Space out notifications so they don't overlap
        xbmc.sleep(3000)


if __name__ == '__main__':
    monitor = xbmc.Monitor()
    xbmc.log('[TheAccountant] Service started', xbmc.LOGINFO)

    # Wait for Kodi to fully start
    xbmc.sleep(15000)

    # Initial check
    if not monitor.abortRequested():
        check_expiry()

    # Check every 12 hours
    while not monitor.abortRequested():
        if monitor.waitForAbort(43200):  # 12 hours
            break
        check_expiry()

    xbmc.log('[TheAccountant] Service stopped', xbmc.LOGINFO)
