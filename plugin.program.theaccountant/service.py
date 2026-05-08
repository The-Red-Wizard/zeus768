"""
The Accountant - Background Service
Checks debrid account expiry on Kodi startup and warns user.
Shows changelog notification when addon is updated.
"""
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import json, os, time

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = os.path.join(ADDON_PATH, 'icon.png')
ADDON_VERSION = ADDON.getAddonInfo('version')
PROFILE_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
INTERNAL_VAULT = os.path.join(PROFILE_PATH, 'vault.json')
DEEP_VAULT = xbmcvfs.translatePath('special://userdata/the_accountant_vault.json')
VAULT_FILE = DEEP_VAULT  # primary location, matches main.py
CHANGELOG_PATH = os.path.join(ADDON_PATH, 'changelog.txt')

WARNING_DAYS = 7  # Warn when less than 7 days left
CRITICAL_DAYS = 2  # Critical warning when less than 2 days


def load_vault():
    for path in (DEEP_VAULT, INTERNAL_VAULT):
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except Exception:
            continue
    return {}


def save_vault(vault):
    """Save vault to both locations (mirrors main.py)."""
    ok = False
    try:
        os.makedirs(os.path.dirname(DEEP_VAULT), exist_ok=True)
        with open(DEEP_VAULT, 'w') as f:
            json.dump(vault, f, indent=2)
        ok = True
    except Exception as e:
        xbmc.log(f'[TheAccountant] save DEEP_VAULT error: {e}', xbmc.LOGERROR)
    try:
        os.makedirs(PROFILE_PATH, exist_ok=True)
        with open(INTERNAL_VAULT, 'w') as f:
            json.dump(vault, f, indent=2)
        ok = True
    except Exception as e:
        xbmc.log(f'[TheAccountant] save INTERNAL_VAULT error: {e}', xbmc.LOGERROR)
    return ok


def check_changelog_notification():
    """Check if addon was updated and show changelog notification.
    User must dismiss the window to continue. Shows on every launch until dismissed for current version.
    """
    vault = load_vault()
    last_seen_version = vault.get('last_seen_version', '')
    
    # If this is a new version, show changelog
    if last_seen_version != ADDON_VERSION:
        xbmc.log(f'[TheAccountant] New version detected: {last_seen_version} -> {ADDON_VERSION}', xbmc.LOGINFO)
        
        # Read changelog
        changelog_content = ""
        try:
            if os.path.exists(CHANGELOG_PATH):
                with open(CHANGELOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                    changelog_content = f.read()
        except Exception as e:
            xbmc.log(f'[TheAccountant] Error reading changelog: {e}', xbmc.LOGERROR)
            changelog_content = f"Version {ADDON_VERSION}\n\nChangelog could not be loaded."
        
        # Format changelog with colors
        formatted_changelog = format_changelog(changelog_content)
        
        # Show in a dialog that must be closed by user
        # Using textviewer which requires user to close it
        dialog = xbmcgui.Dialog()
        
        # First show a notification
        dialog.notification(
            'The Accountant Updated!',
            f'Updated to version {ADDON_VERSION}',
            ADDON_ICON,
            5000
        )
        
        # Wait a moment for notification
        xbmc.sleep(1000)
        
        # Show changelog in textviewer - user must close this
        dialog.textviewer(
            f'The Accountant - What\'s New in v{ADDON_VERSION}',
            formatted_changelog
        )
        
        # After user closes the dialog, mark this version as seen
        vault['last_seen_version'] = ADDON_VERSION
        save_vault(vault)
        xbmc.log(f'[TheAccountant] Changelog shown and dismissed for version {ADDON_VERSION}', xbmc.LOGINFO)


def format_changelog(content):
    """Format changelog with Kodi color tags for better readability"""
    lines = content.split('\n')
    formatted_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Version headers - cyan
        if stripped.startswith('v') and '(' in stripped:
            formatted_lines.append(f'[COLOR cyan][B]{line}[/B][/COLOR]')
        # Section headers with === - yellow
        elif '===' in stripped:
            formatted_lines.append(f'[COLOR yellow]{line}[/COLOR]')
        # NEW/FIXED/IMPROVEMENTS headers
        elif stripped.startswith('NEW') or stripped.startswith('FIXED') or stripped.startswith('BUG FIX'):
            formatted_lines.append(f'[COLOR lime]{line}[/COLOR]')
        elif stripped.startswith('IMPROVEMENTS') or stripped.startswith('PRESERVED'):
            formatted_lines.append(f'[COLOR orange]{line}[/COLOR]')
        # Bullet points
        elif stripped.startswith('-'):
            formatted_lines.append(f'[COLOR white]{line}[/COLOR]')
        # Numbered items
        elif stripped and stripped[0].isdigit() and '.' in stripped[:3]:
            formatted_lines.append(f'[COLOR lightgray]{line}[/COLOR]')
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)


def check_trakt():
    """Refresh Trakt token silently, or prompt user with a countdown re-pair dialog."""
    vault = load_vault()
    if not vault.get('trakt_token'):
        return
    try:
        from resources.lib.auth_manager import check_trakt_expiry
        result = check_trakt_expiry(vault, save_vault)
        xbmc.log(f'[TheAccountant] Trakt check: {result}', xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f'[TheAccountant] Trakt check error: {e}', xbmc.LOGERROR)


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

    # Check for changelog notification on startup (user must dismiss)
    if not monitor.abortRequested():
        check_changelog_notification()

    # Initial expiry check
    if not monitor.abortRequested():
        check_expiry()
        check_trakt()

    # Check every 12 hours
    while not monitor.abortRequested():
        if monitor.waitForAbort(43200):  # 12 hours
            break
        check_expiry()
        check_trakt()

    xbmc.log('[TheAccountant] Service stopped', xbmc.LOGINFO)
