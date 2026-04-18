"""
The Accountant - Background Service
- Warns user when debrid accounts are about to expire.
- Silently auto-syncs vault credentials to every installed addon once
  every 24h (can be disabled via vault flag 'auto_sync_enabled').
"""
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import json, os, time

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = os.path.join(ADDON_PATH, 'icon.png')

# Vault lives in userdata - match main.py's DEEP_VAULT
DEEP_VAULT = xbmcvfs.translatePath('special://userdata/the_accountant_vault.json')
PROFILE_DIR = xbmcvfs.translatePath('special://profile/addon_data/plugin.program.theaccountant/')
INTERNAL_VAULT = os.path.join(PROFILE_DIR, 'vault.json')

WARNING_DAYS = 7   # Warn when less than 7 days left
CRITICAL_DAYS = 2  # Critical warning when less than 2 days
AUTO_SYNC_INTERVAL = 86400  # 24 hours between silent syncs


def load_vault():
    """Load vault from the same locations main.py uses."""
    for path in (DEEP_VAULT, INTERNAL_VAULT):
        if os.path.isfile(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def save_vault(vault):
    """Persist vault back to both locations so main.py sees the same state."""
    try:
        os.makedirs(PROFILE_DIR, exist_ok=True)
        for path in (DEEP_VAULT, INTERNAL_VAULT):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump(vault, f, indent=2)
    except Exception as e:
        xbmc.log(f'[Accountant] save_vault failed: {e}', xbmc.LOGWARNING)


def check_expiry():
    """Check all debrid accounts and warn if expiring soon."""
    vault = load_vault()
    warnings = []

    checks = [
        ('Real-Debrid', 'rd_token', 'get_rd_account_info'),
        ('Premiumize',  'pm_token', 'get_pm_account_info'),
        ('AllDebrid',   'ad_token', 'get_ad_account_info'),
    ]

    for service, key, fn_name in checks:
        token = vault.get(key, '')
        if not token:
            continue
        try:
            from resources.lib import auth_manager
            info = getattr(auth_manager, fn_name)(token)
            if not info:
                continue
            days = info.get('days_left', 0)
            if days <= 0:
                warnings.append((service, 'EXPIRED', 0))
            elif days <= CRITICAL_DAYS:
                warnings.append((service, 'EXPIRING', days))
            elif days <= WARNING_DAYS:
                warnings.append((service, 'WARNING', days))
        except Exception as e:
            xbmc.log(f'[Accountant] expiry check {service} failed: {e}', xbmc.LOGDEBUG)

    for service, level, days in warnings:
        if level == 'EXPIRED':
            xbmcgui.Dialog().notification(
                f'{service} EXPIRED',
                'Your subscription has expired. Renew now.',
                ADDON_ICON, 10000
            )
        elif level == 'EXPIRING':
            xbmcgui.Dialog().notification(
                f'{service} Expiring',
                f'Only {days} day{"s" if days != 1 else ""} left. Renew soon.',
                ADDON_ICON, 8000
            )
        elif level == 'WARNING':
            xbmcgui.Dialog().notification(
                f'{service} Reminder',
                f'{days} days remaining on your subscription.',
                ADDON_ICON, 5000
            )
        xbmc.sleep(3000)


def maybe_auto_sync():
    """Run a silent credential sync at most once per AUTO_SYNC_INTERVAL.

    Controlled by vault flag 'auto_sync_enabled' (default: True).
    Timestamp stored in vault as 'last_auto_sync'.
    """
    vault = load_vault()
    if not vault:
        return
    # Default to enabled; user can set to 'false' via main.py to opt out.
    enabled = str(vault.get('auto_sync_enabled', 'true')).lower() not in ('0', 'false', 'no', 'off')
    if not enabled:
        return
    last = 0
    try:
        last = float(vault.get('last_auto_sync', 0) or 0)
    except Exception:
        last = 0
    if (time.time() - last) < AUTO_SYNC_INTERVAL:
        return
    try:
        from resources.lib.auth_manager import sync_to_all_addons
        synced = sync_to_all_addons(vault, silent=True)
        vault['last_auto_sync'] = int(time.time())
        save_vault(vault)
        if synced:
            xbmcgui.Dialog().notification(
                'The Accountant',
                f'Auto-synced {len(synced)} addon{"s" if len(synced) != 1 else ""}',
                ADDON_ICON, 4000
            )
    except Exception as e:
        xbmc.log(f'[Accountant] auto-sync failed: {e}', xbmc.LOGERROR)


if __name__ == '__main__':
    monitor = xbmc.Monitor()
    xbmc.log('[TheAccountant] Service started', xbmc.LOGINFO)

    # Wait for Kodi to fully start
    xbmc.sleep(15000)

    if not monitor.abortRequested():
        check_expiry()
        maybe_auto_sync()

    # Loop every hour; internal throttles handle actual cadence.
    while not monitor.abortRequested():
        if monitor.waitForAbort(3600):  # 1 hour tick
            break
        # Expiry check runs every 12h
        now = int(time.time())
        if not hasattr(monitor, '_last_expiry') or (now - getattr(monitor, '_last_expiry', 0)) >= 43200:
            try:
                check_expiry()
            except Exception:
                pass
            monitor._last_expiry = now
        maybe_auto_sync()

    xbmc.log('[TheAccountant] Service stopped', xbmc.LOGINFO)
