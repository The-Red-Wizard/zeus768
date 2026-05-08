import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs
import json, os, sys, shutil, urllib.parse, urllib.request, time

# --- CRITICAL: PREVENT STARTUP CRASH ---
try:
    ADDON = xbmcaddon.Addon()
    HANDLE = int(sys.argv[1])
    ADDON_ICON = ADDON.getAddonInfo('icon')
    ADDON_FANART = ADDON.getAddonInfo('fanart')
    ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
    MEDIA_PATH = os.path.join(ADDON_PATH, 'resources', 'media')
except Exception as e:
    xbmc.log(f"The Accountant: Initial load error: {str(e)}", xbmc.LOGERROR)

# Locked Paths
PROFILE_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
INTERNAL_VAULT = os.path.join(PROFILE_PATH, 'vault.json')
DEEP_VAULT = xbmcvfs.translatePath('special://userdata/the_accountant_vault.json')
FAV_FILE = xbmcvfs.translatePath('special://userdata/favourites.xml')
DEEP_FAV = xbmcvfs.translatePath('special://userdata/the_accountant_favs.xml')
IPTV_VAULT = os.path.join(PROFILE_PATH, 'iptv_vault.json')

# Kodi System Paths
KODI_HOME = xbmcvfs.translatePath('special://home/')
KODI_USERDATA = xbmcvfs.translatePath('special://userdata/')
KODI_TEMP = xbmcvfs.translatePath('special://temp/')
KODI_ADDONS = xbmcvfs.translatePath('special://home/addons/')
KODI_PACKAGES = xbmcvfs.translatePath('special://home/addons/packages/')
KODI_THUMBNAILS = xbmcvfs.translatePath('special://userdata/Thumbnails/')
KODI_DATABASE = xbmcvfs.translatePath('special://userdata/Database/')
KODI_ADDON_DATA = xbmcvfs.translatePath('special://userdata/addon_data/')

def get_art(icon_name):
    """Get icon path with fallback to addon icon"""
    if not icon_name:
        return ADDON_ICON
    icon_path = os.path.join(MEDIA_PATH, icon_name)
    return icon_path if xbmcvfs.exists(icon_path) else ADDON_ICON

def notify(title, message, duration=3000):
    """Show notification"""
    xbmcgui.Dialog().notification(title, message, ADDON_ICON, duration)

def get_size(path):
    """Get folder size in MB"""
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total += os.path.getsize(fp)
    except:
        pass
    return total / (1024 * 1024)

def delete_folder_contents(folder_path, extensions=None):
    """Delete contents of a folder, optionally filtering by extension"""
    deleted = 0
    try:
        if not os.path.exists(folder_path):
            return 0
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                if extensions is None or any(f.endswith(ext) for ext in extensions):
                    try:
                        os.remove(os.path.join(root, f))
                        deleted += 1
                    except:
                        pass
    except:
        pass
    return deleted

# ============================================
# SPEED OPTIMIZER
# ============================================
def speed_optimizer():
    """One-click speed optimization"""
    dialog = xbmcgui.Dialog()
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("The Accountant", "Analyzing system...")
    
    # Calculate sizes before cleanup
    cache_size = get_size(KODI_TEMP)
    thumb_size = get_size(KODI_THUMBNAILS)
    pkg_size = get_size(KODI_PACKAGES)
    total_before = cache_size + thumb_size + pkg_size
    
    pDialog.update(10, "Clearing temporary cache...")
    delete_folder_contents(KODI_TEMP)
    
    pDialog.update(30, "Clearing packages...")
    delete_folder_contents(KODI_PACKAGES, ['.zip'])
    
    pDialog.update(50, "Optimizing thumbnails...")
    # Clear old thumbnails (keeping recent ones)
    try:
        thumb_count = 0
        for root, dirs, files in os.walk(KODI_THUMBNAILS):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    if os.path.getmtime(fp) < (time.time() - 30*24*60*60):  # 30 days old
                        os.remove(fp)
                        thumb_count += 1
                except:
                    pass
    except:
        pass
    
    pDialog.update(70, "Clearing addon cache...")
    # Clear common addon caches
    addon_cache_paths = [
        os.path.join(KODI_ADDON_DATA, 'plugin.video.youtube', 'kodion', 'cache'),
        os.path.join(KODI_ADDON_DATA, 'plugin.video.themoviedb.helper', 'cache'),
        os.path.join(KODI_ADDON_DATA, 'script.extendedinfo', 'cache'),
    ]
    for cache_path in addon_cache_paths:
        if os.path.exists(cache_path):
            delete_folder_contents(cache_path)
    
    pDialog.update(90, "Finalizing...")
    
    # Calculate savings
    total_after = get_size(KODI_TEMP) + get_size(KODI_THUMBNAILS) + get_size(KODI_PACKAGES)
    saved = total_before - total_after
    
    pDialog.close()
    
    dialog.ok("Speed Optimizer Complete", 
              f"Freed approximately {saved:.1f} MB\nSystem optimized! Restart Kodi for best results.")

# ============================================
# AUTHENTICATION MANAGER
# ============================================
def auth_menu():
    """Authentication sub-menu with device code auth"""
    items = [
        ("Real-Debrid (Device Code)", "auth_rd", "rd.png"),
        ("Premiumize (API Key)", "auth_pm", "pm.png"),
        ("AllDebrid (PIN Code)", "auth_ad", "ad.png"),
        ("TorBox (API Key)", "auth_tb", "rd.png"),
        ("Trakt (Device Code)", "auth_trakt", "trakt.png"),
        ("TMDB API Key Setup", "auth_tmdb", "tmdb.png"),
        ("--- Account Info ---", "spacer", ""),
        ("View Account Cards", "account_cards", "auth.png"),
        ("--- Sync ---", "spacer", ""),
        ("Sync All to Addons", "sync_all", "sync.png"),
        ("Back to Main Menu", "main", "restore.png")
    ]
    for label, act, icon in items:
        li = xbmcgui.ListItem(label=label)
        if act == "spacer":
            li.setArt({'icon': ADDON_ICON, 'thumb': ADDON_ICON, 'fanart': ADDON_FANART})
            xbmcplugin.addDirectoryItem(HANDLE, "", li, False)
        else:
            art = get_art(icon)
            li.setArt({'icon': art, 'thumb': art, 'fanart': ADDON_FANART})
            url = f"{sys.argv[0]}?action={act}"
            xbmcplugin.addDirectoryItem(HANDLE, url, li, True if act == 'main' else False)
    xbmcplugin.endOfDirectory(HANDLE)

def load_vault():
    """Load vault data"""
    vault = {}
    if xbmcvfs.exists(DEEP_VAULT):
        try:
            with open(DEEP_VAULT, 'r') as f:
                vault = json.load(f)
        except:
            pass
    return vault

def save_vault(vault):
    """Save vault data"""
    try:
        os.makedirs(os.path.dirname(DEEP_VAULT), exist_ok=True)
        with open(DEEP_VAULT, 'w') as f:
            json.dump(vault, f, indent=2)
        # Also save to internal vault
        os.makedirs(PROFILE_PATH, exist_ok=True)
        with open(INTERNAL_VAULT, 'w') as f:
            json.dump(vault, f, indent=2)
        return True
    except Exception as e:
        xbmc.log(f"The Accountant: Save vault error: {str(e)}", xbmc.LOGERROR)
        return False

def auth_real_debrid():
    """Real-Debrid device code auth"""
    from resources.lib.auth_manager import auth_rd_device_code
    vault = load_vault()
    auth_rd_device_code(vault, save_vault)

def auth_premiumize():
    """Premiumize API key auth"""
    from resources.lib.auth_manager import auth_pm_apikey
    vault = load_vault()
    auth_pm_apikey(vault, save_vault)

def auth_alldebrid():
    """AllDebrid PIN auth"""
    from resources.lib.auth_manager import auth_ad_pin
    vault = load_vault()
    auth_ad_pin(vault, save_vault)

def auth_trakt():
    """Trakt device code auth"""
    from resources.lib.auth_manager import auth_trakt_device
    vault = load_vault()
    auth_trakt_device(vault, save_vault)

def auth_torbox():
    """TorBox API key auth"""
    from resources.lib.auth_manager import auth_tb_apikey
    vault = load_vault()
    auth_tb_apikey(vault, save_vault)

def auth_tmdb():
    """TMDB API setup"""
    dialog = xbmcgui.Dialog()
    vault = load_vault()
    
    current_key = vault.get('tmdb_api_key', 'Not Set')
    display_key = current_key[:15] + '...' if len(current_key) > 15 else current_key
    
    choice = dialog.select("TMDB API", [
        f"Current: {display_key}",
        "Enter TMDB API Key (v3)",
        "Clear TMDB Key",
        "Sync to TMDB Helper",
        "Help: How to get TMDB Key"
    ])
    
    if choice == 1:
        key = dialog.input("Enter TMDB API Key")
        if key:
            vault['tmdb_api_key'] = key
            if save_vault(vault):
                notify("TMDB", "API Key Saved!")
    elif choice == 2:
        vault.pop('tmdb_api_key', None)
        save_vault(vault)
        notify("TMDB", "Key Cleared")
    elif choice == 3:
        sync_tmdb_helper()
    elif choice == 4:
        dialog.ok("TMDB Help",
                  "1. Go to themoviedb.org\n2. Create account, go to Settings > API\n3. Request API key and copy v3 auth")

def sync_tmdb_helper():
    """Sync TMDB to TMDBHelper addon"""
    # Skip silently if TMDB Helper isn't installed - don't let Kodi
    # pop an 'Install addon?' dialog during bulk sync flows.
    if not xbmc.getCondVisibility('System.HasAddon(plugin.video.themoviedb.helper)'):
        notify("Sync Failed", "TMDB Helper not installed")
        return
    try:
        tmdb_addon = xbmcaddon.Addon('plugin.video.themoviedb.helper')
        vault = load_vault()
        
        api_key = vault.get('tmdb_api_key', '')
        if api_key:
            tmdb_addon.setSetting('tmdb_api_key', api_key)
            tmdb_addon.setSetting('use_custom_tmdb_api', 'true')
            notify("Accountant", "TMDB Helper Synced!")
        else:
            xbmcgui.Dialog().ok("Sync Failed", "No TMDB API key stored in vault")
    except:
        notify("Sync Failed", "TMDB Helper not installed")

def sync_all_addons():
    """Sync all credentials to ALL detected addons on device"""
    from resources.lib.auth_manager import sync_to_all_addons
    vault = load_vault()
    sync_to_all_addons(vault, save_vault)


def show_account_cards():
    """Show detailed account info for all services with custom Window XLM skin"""
    from resources.lib import auth_manager
    from resources.lib.account_cards_window import show_account_cards_window
    
    vault = load_vault()
    pDialog = xbmcgui.DialogProgress()
    pDialog.create('The Accountant', 'Fetching account details...')

    # Collect account info for all services
    account_info = {}

    # Real-Debrid
    pDialog.update(15, 'Checking Real-Debrid...')
    rd_token = vault.get('rd_token', '')
    if rd_token:
        info = auth_manager.get_rd_account_info(rd_token)
        if info:
            account_info['rd'] = info

    # Premiumize
    pDialog.update(30, 'Checking Premiumize...')
    pm_token = vault.get('pm_token', '')
    if pm_token:
        info = auth_manager.get_pm_account_info(pm_token)
        if info:
            account_info['pm'] = info

    # AllDebrid
    pDialog.update(45, 'Checking AllDebrid...')
    ad_token = vault.get('ad_token', '')
    if ad_token:
        info = auth_manager.get_ad_account_info(ad_token)
        if info:
            account_info['ad'] = info

    # Trakt
    pDialog.update(60, 'Checking Trakt...')
    trakt_token = vault.get('trakt_token', '')
    if trakt_token:
        info = auth_manager.get_trakt_account_info(trakt_token)
        if info:
            account_info['trakt'] = info

    # TorBox
    pDialog.update(75, 'Checking TorBox...')
    tb_token = vault.get('tb_token', '')
    if tb_token:
        account_info['tb'] = {'status': 'Authorized'}

    # TMDB
    pDialog.update(90, 'Checking TMDB...')
    tmdb_key = vault.get('tmdb_api_key', '')
    if tmdb_key:
        tmdb_info = auth_manager.get_tmdb_info(tmdb_key)
        account_info['tmdb'] = tmdb_info or {'status': 'API Key Set'}

    pDialog.close()

    # Show custom Window XLM skin
    show_account_cards_window(vault, account_info)

# ============================================
# IPTV VAULT
# ============================================
def iptv_vault():
    """IPTV credentials vault"""
    dialog = xbmcgui.Dialog()
    
    # Load IPTV vault
    iptv_data = {}
    if os.path.exists(IPTV_VAULT):
        try:
            with open(IPTV_VAULT, 'r') as f:
                iptv_data = json.load(f)
        except:
            pass
    
    providers = list(iptv_data.keys()) if iptv_data else []
    
    options = ["Add New IPTV Provider"]
    options.extend([f"Edit: {p}" for p in providers])
    options.extend([f"Delete: {p}" for p in providers])
    if providers:
        options.append("Export IPTV to Addon")
    
    choice = dialog.select("IPTV Vault", options)
    
    if choice == 0:  # Add new
        name = dialog.input("Provider Name (e.g., MyIPTV)")
        if name:
            # v4.8.0: ask for portal type so we can target Poseidon Player
            # correctly (Xtreme Codes vs STB MAC).
            ptype = dialog.select("Portal Type", [
                "Xtreme Codes (URL + username + password)",
                "STB MAC (portal URL + MAC address)",
            ])
            if ptype == 1:
                portal_url = dialog.input("Portal URL")
                mac = dialog.input("MAC Address (AA:BB:CC:DD:EE:FF)")
                iptv_data[name] = {
                    'type': 'mac',
                    'portal_url': (portal_url or '').rstrip('/'),
                    'mac': (mac or '').upper(),
                }
            else:
                url = dialog.input("M3U URL or Server URL")
                username = dialog.input("Username (optional)")
                password = dialog.input("Password (optional)")
                iptv_data[name] = {
                    'type': 'xtream',
                    'url': url,
                    'username': username,
                    'password': password,
                }

            os.makedirs(PROFILE_PATH, exist_ok=True)
            with open(IPTV_VAULT, 'w') as f:
                json.dump(iptv_data, f, indent=2)
            notify("IPTV Vault", f"{name} saved!")
            
    elif choice > 0 and choice <= len(providers):  # Edit
        provider = providers[choice - 1]
        data = iptv_data[provider]
        
        edit_choice = dialog.select(f"Edit {provider}", [
            f"URL: {data.get('url', '')[:30]}...",
            f"Username: {data.get('username', 'Not set')}",
            f"Password: {'*****' if data.get('password') else 'Not set'}",
            "Save Changes"
        ])
        
        if edit_choice == 0:
            data['url'] = dialog.input("M3U URL", data.get('url', ''))
        elif edit_choice == 1:
            data['username'] = dialog.input("Username", data.get('username', ''))
        elif edit_choice == 2:
            data['password'] = dialog.input("Password", data.get('password', ''))
        
        iptv_data[provider] = data
        with open(IPTV_VAULT, 'w') as f:
            json.dump(iptv_data, f, indent=2)
            
    elif choice > len(providers) and choice <= len(providers) * 2:  # Delete
        provider = providers[choice - len(providers) - 1]
        if dialog.yesno("Confirm", f"Delete {provider}?"):
            del iptv_data[provider]
            with open(IPTV_VAULT, 'w') as f:
                json.dump(iptv_data, f, indent=2)
            notify("IPTV Vault", f"{provider} deleted")
            
    elif providers and choice == len(options) - 1:  # Export to addon
        export_iptv_to_addon(iptv_data)

def export_iptv_to_addon(iptv_data):
    """Export IPTV credentials to Poseidon Player ONLY.

    v4.8.0: No longer writes to pvr.iptvsimple. Users requested that IPTV
    credentials stay self-contained inside Poseidon Player so that Simple IPTV
    Client is never mutated by The Accountant.
    """
    dialog = xbmcgui.Dialog()
    providers = list(iptv_data.keys())
    if not providers:
        dialog.ok("No providers", "Add an IPTV provider to the vault first.")
        return

    choice = dialog.select("Select Provider to Export", providers)
    if choice < 0:
        return
    provider = providers[choice]
    data = iptv_data[provider]

    # Target: Poseidon Player only.
    if not xbmc.getCondVisibility('System.HasAddon(plugin.video.poseidonplayer)'):
        dialog.ok(
            "Poseidon Player not installed",
            "IPTV details can only be exported to Poseidon Player.",
            "Install Poseidon Player from the repo and try again.",
        )
        return

    try:
        poseidon = xbmcaddon.Addon('plugin.video.poseidonplayer')
    except Exception as e:
        dialog.ok("Export Failed", f"Could not access Poseidon Player ({e})")
        return

    # Poseidon Player supports two portal modes; write whichever matches the
    # vault entry. Vault shape is flexible so we detect by key presence.
    if data.get('mac') or data.get('portal_url'):
        poseidon.setSetting('portal_mode', 'mac')
        poseidon.setSetting('portal_url', data.get('portal_url') or data.get('url', ''))
        poseidon.setSetting('mac_address', data.get('mac', '').upper())
        mode_label = 'STB MAC'
    else:
        poseidon.setSetting('portal_mode', 'xtream')
        poseidon.setSetting('dns', data.get('url', '') or data.get('dns', ''))
        poseidon.setSetting('username', data.get('username', '') or data.get('user', ''))
        poseidon.setSetting('password', data.get('password', '') or data.get('pass', ''))
        mode_label = 'Xtreme Codes'

    notify("IPTV Export", f"{provider} exported to Poseidon Player ({mode_label})")

# ============================================
# FAVOURITES VAULT
# ============================================
def favourites_vault():
    """Favourites backup and restore"""
    dialog = xbmcgui.Dialog()
    
    choice = dialog.select("Favourites Vault", [
        "Backup Current Favourites",
        "Restore Favourites from Vault",
        "View Backup Status",
        "Clear Favourites Backup"
    ])
    
    if choice == 0:  # Backup
        if xbmcvfs.exists(FAV_FILE):
            shutil.copy2(FAV_FILE, DEEP_FAV)
            notify("Favourites", "Backup saved!")
        else:
            dialog.ok("Backup Failed", "No favourites file found")
            
    elif choice == 1:  # Restore
        if xbmcvfs.exists(DEEP_FAV):
            if dialog.yesno("Confirm", "This will replace your current favourites. Continue?"):
                shutil.copy2(DEEP_FAV, FAV_FILE)
                dialog.ok("Favourites Restored", "Restart Kodi to see changes")
        else:
            dialog.ok("Restore Failed", "No backup found in vault")
            
    elif choice == 2:  # Status
        current_exists = "Yes" if xbmcvfs.exists(FAV_FILE) else "No"
        backup_exists = "Yes" if xbmcvfs.exists(DEEP_FAV) else "No"
        
        backup_date = "Unknown"
        if xbmcvfs.exists(DEEP_FAV):
            try:
                mtime = os.path.getmtime(DEEP_FAV)
                backup_date = time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))
            except:
                pass
        
        dialog.ok("Favourites Status",
                  f"Current Favourites: {current_exists}\nBackup Exists: {backup_exists}\nBackup Date: {backup_date}")
                  
    elif choice == 3:  # Clear
        if xbmcvfs.exists(DEEP_FAV):
            if dialog.yesno("Confirm", "Delete favourites backup?"):
                os.remove(DEEP_FAV)
                notify("Favourites", "Backup cleared")

# ============================================
# USB BACKUP TOOL
# ============================================
def usb_manager():
    """USB backup and restore"""
    dialog = xbmcgui.Dialog()
    
    choice = dialog.select("USB Backup Tool", [
        "Export Vault to USB",
        "Import Vault from USB",
        "Export Full Backup to USB",
        "Import Full Backup from USB"
    ])
    
    if choice == -1:
        return
        
    usb_path = dialog.browse(0, 'Select USB Folder', 'files')
    if not usb_path:
        return

    if choice == 0:  # Export vault
        exported = []
        for src, name in [(DEEP_VAULT, 'vault.json'), (DEEP_FAV, 'favs.xml'), (IPTV_VAULT, 'iptv.json')]:
            if xbmcvfs.exists(src):
                shutil.copy2(src, os.path.join(usb_path, name))
                exported.append(name)
        dialog.ok("Export Complete", f"Exported: {', '.join(exported)}" if exported else "No data to export")
        
    elif choice == 1:  # Import vault
        imported = []
        mappings = [('vault.json', DEEP_VAULT), ('favs.xml', DEEP_FAV), ('iptv.json', IPTV_VAULT)]
        for name, dest in mappings:
            src = os.path.join(usb_path, name)
            if xbmcvfs.exists(src):
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(src, dest)
                imported.append(name)
        dialog.ok("Import Complete", f"Imported: {', '.join(imported)}" if imported else "No backup files found")
        
    elif choice == 2:  # Full backup
        backup_folder = os.path.join(usb_path, 'accountant_full_backup')
        os.makedirs(backup_folder, exist_ok=True)
        
        pDialog = xbmcgui.DialogProgress()
        pDialog.create("Full Backup", "Backing up...")
        
        # Backup addon_data
        pDialog.update(25, "Backing up addon data...")
        addon_backup = os.path.join(backup_folder, 'addon_data')
        if os.path.exists(KODI_ADDON_DATA):
            try:
                shutil.copytree(KODI_ADDON_DATA, addon_backup, dirs_exist_ok=True)
            except:
                pass
        
        # Backup favourites
        pDialog.update(50, "Backing up favourites...")
        if xbmcvfs.exists(FAV_FILE):
            shutil.copy2(FAV_FILE, os.path.join(backup_folder, 'favourites.xml'))
        
        # Backup vault files
        pDialog.update(75, "Backing up vault...")
        for src, name in [(DEEP_VAULT, 'vault.json'), (IPTV_VAULT, 'iptv.json')]:
            if xbmcvfs.exists(src):
                shutil.copy2(src, os.path.join(backup_folder, name))
        
        pDialog.close()
        dialog.ok("Full Backup Complete", f"Saved to: {backup_folder}")
        
    elif choice == 3:  # Full restore
        backup_folder = os.path.join(usb_path, 'accountant_full_backup')
        if not os.path.exists(backup_folder):
            dialog.ok("Restore Failed", "No full backup found at selected location")
            return
            
        if dialog.yesno("Confirm Full Restore", "This will overwrite current settings. Continue?"):
            pDialog = xbmcgui.DialogProgress()
            pDialog.create("Full Restore", "Restoring...")
            
            # Restore addon_data
            pDialog.update(50, "Restoring addon data...")
            addon_backup = os.path.join(backup_folder, 'addon_data')
            if os.path.exists(addon_backup):
                try:
                    shutil.copytree(addon_backup, KODI_ADDON_DATA, dirs_exist_ok=True)
                except:
                    pass
            
            # Restore other files
            pDialog.update(75, "Restoring vault...")
            mappings = [
                ('favourites.xml', FAV_FILE),
                ('vault.json', DEEP_VAULT),
                ('iptv.json', IPTV_VAULT)
            ]
            for name, dest in mappings:
                src = os.path.join(backup_folder, name)
                if os.path.exists(src):
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(src, dest)
            
            pDialog.close()
            dialog.ok("Full Restore Complete", "Restart Kodi to apply changes")

# ============================================
# ONE-CLICK RESTORE
# ============================================
def one_click_restore():
    """Restore everything from vault"""
    dialog = xbmcgui.Dialog()
    
    if not dialog.yesno("One-Click Restore", 
                        "This will restore all saved credentials and favourites.",
                        "Continue?"):
        return
    
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("The Accountant", "Restoring...")
    
    restored = []
    
    # Restore vault
    pDialog.update(25, "Restoring vault...")
    if xbmcvfs.exists(DEEP_VAULT):
        os.makedirs(PROFILE_PATH, exist_ok=True)
        shutil.copy2(DEEP_VAULT, INTERNAL_VAULT)
        restored.append("Vault")
    
    # Restore favourites
    pDialog.update(50, "Restoring favourites...")
    if xbmcvfs.exists(DEEP_FAV):
        shutil.copy2(DEEP_FAV, FAV_FILE)
        restored.append("Favourites")
    
    # Sync to addons
    pDialog.update(75, "Syncing to addons...")
    sync_tmdb_helper()
    
    pDialog.close()
    
    if restored:
        dialog.ok("Restore Complete", f"Restored: {', '.join(restored)}\nRestart Kodi for full effect")
    else:
        dialog.ok("Restore", "No backup data found to restore")

# ============================================
# REPAIR VIDEO ADDONS
# ============================================
def repair_addons():
    """Repair and fix video addons"""
    dialog = xbmcgui.Dialog()
    
    choice = dialog.select("Repair Video Addons", [
        "Clear All Addon Cache",
        "Reset Addon Databases",
        "Force Addon Refresh",
        "Fix Broken Dependencies",
        "Repair Specific Addon"
    ])
    
    if choice == 0:  # Clear cache
        clear_addon_cache()
    elif choice == 1:  # Reset databases
        reset_addon_databases()
    elif choice == 2:  # Force refresh
        force_addon_refresh()
    elif choice == 3:  # Fix dependencies
        fix_dependencies()
    elif choice == 4:  # Repair specific
        repair_specific_addon()

def clear_addon_cache():
    """Clear all addon caches"""
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("Clearing Cache", "Scanning addons...")
    
    cache_cleared = 0
    addon_data_path = KODI_ADDON_DATA
    
    if os.path.exists(addon_data_path):
        addons = os.listdir(addon_data_path)
        total = len(addons)
        
        for i, addon in enumerate(addons):
            pDialog.update(int((i/total)*100), f"Checking {addon}...")
            addon_path = os.path.join(addon_data_path, addon)
            
            # Common cache folder names
            cache_folders = ['cache', 'Cache', 'temp', 'Temp', 'tmp']
            for cache_name in cache_folders:
                cache_path = os.path.join(addon_path, cache_name)
                if os.path.exists(cache_path):
                    try:
                        shutil.rmtree(cache_path)
                        cache_cleared += 1
                    except:
                        pass
    
    pDialog.close()
    xbmcgui.Dialog().ok("Cache Cleared", f"Cleared {cache_cleared} cache folders")

def reset_addon_databases():
    """Reset addon databases"""
    dialog = xbmcgui.Dialog()
    
    if not dialog.yesno("Warning", "This will reset addon databases.", "You may lose some addon settings. Continue?"):
        return
    
    db_path = KODI_DATABASE
    deleted = 0
    
    if os.path.exists(db_path):
        for f in os.listdir(db_path):
            if f.startswith('Addons') and f.endswith('.db'):
                try:
                    os.remove(os.path.join(db_path, f))
                    deleted += 1
                except:
                    pass
    
    dialog.ok("Databases Reset", f"Deleted {deleted} database(s)", "Restart Kodi to rebuild")

def force_addon_refresh():
    """Force Kodi to refresh addons"""
    xbmc.executebuiltin('UpdateAddonRepos')
    xbmc.executebuiltin('UpdateLocalAddons')
    notify("Addon Refresh", "Refreshing addons...")

def fix_dependencies():
    """Attempt to fix broken dependencies"""
    dialog = xbmcgui.Dialog()
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("Fixing Dependencies", "Scanning...")
    
    # Force update repos
    pDialog.update(25, "Updating repositories...")
    xbmc.executebuiltin('UpdateAddonRepos')
    xbmc.sleep(2000)
    
    # Check for broken addons
    pDialog.update(50, "Checking addons...")
    xbmc.executebuiltin('UpdateLocalAddons')
    xbmc.sleep(2000)
    
    pDialog.update(75, "Cleaning up...")
    # Clear packages to force re-download
    delete_folder_contents(KODI_PACKAGES, ['.zip'])
    
    pDialog.close()
    dialog.ok("Dependencies", "Dependency check complete\nRestart Kodi if issues persist")

def repair_specific_addon():
    """Repair a specific addon"""
    dialog = xbmcgui.Dialog()
    
    # List video addons
    video_addons = []
    addon_path = KODI_ADDONS
    
    if os.path.exists(addon_path):
        for addon in os.listdir(addon_path):
            if addon.startswith('plugin.video.'):
                video_addons.append(addon)
    
    if not video_addons:
        dialog.ok("No Addons", "No video addons found")
        return
    
    choice = dialog.select("Select Addon to Repair", video_addons)
    if choice >= 0:
        addon_id = video_addons[choice]
        
        repair_choice = dialog.select(f"Repair {addon_id}", [
            "Clear Addon Cache",
            "Clear Addon Data (Full Reset)",
            "Reinstall Addon"
        ])
        
        if repair_choice == 0:
            addon_data = os.path.join(KODI_ADDON_DATA, addon_id)
            cache_paths = ['cache', 'Cache', 'temp']
            for cp in cache_paths:
                full_path = os.path.join(addon_data, cp)
                if os.path.exists(full_path):
                    shutil.rmtree(full_path)
            notify("Repair", f"Cache cleared for {addon_id}")
            
        elif repair_choice == 1:
            if dialog.yesno("Warning", f"This will delete ALL data for {addon_id}\nContinue?"):
                addon_data = os.path.join(KODI_ADDON_DATA, addon_id)
                if os.path.exists(addon_data):
                    shutil.rmtree(addon_data)
                notify("Repair", f"Data cleared for {addon_id}")
                
        elif repair_choice == 2:
            xbmc.executebuiltin(f'InstallAddon({addon_id})')
            notify("Repair", "Reinstalling addon...")

# ============================================
# CLEAR CACHE (MANUAL)
# ============================================
def clear_cache_menu():
    """Manual cache clearing options"""
    dialog = xbmcgui.Dialog()
    
    # Calculate sizes
    temp_size = get_size(KODI_TEMP)
    thumb_size = get_size(KODI_THUMBNAILS)
    pkg_size = get_size(KODI_PACKAGES)
    
    choice = dialog.select("Clear Cache", [
        f"Clear Temp Cache ({temp_size:.1f} MB)",
        f"Clear Thumbnails ({thumb_size:.1f} MB)",
        f"Clear Packages ({pkg_size:.1f} MB)",
        "Clear All Cache",
        "Clear Specific Addon Cache"
    ])
    
    if choice == 0:
        if dialog.yesno("Confirm", f"Clear {temp_size:.1f} MB of temp cache?"):
            delete_folder_contents(KODI_TEMP)
            notify("Cache", "Temp cache cleared")
            
    elif choice == 1:
        if dialog.yesno("Confirm", f"Clear {thumb_size:.1f} MB of thumbnails?"):
            delete_folder_contents(KODI_THUMBNAILS)
            notify("Cache", "Thumbnails cleared")
            
    elif choice == 2:
        if dialog.yesno("Confirm", f"Clear {pkg_size:.1f} MB of packages?"):
            delete_folder_contents(KODI_PACKAGES, ['.zip'])
            notify("Cache", "Packages cleared")
            
    elif choice == 3:
        total = temp_size + thumb_size + pkg_size
        if dialog.yesno("Confirm", f"Clear ALL cache ({total:.1f} MB)?"):
            delete_folder_contents(KODI_TEMP)
            delete_folder_contents(KODI_THUMBNAILS)
            delete_folder_contents(KODI_PACKAGES, ['.zip'])
            notify("Cache", "All cache cleared")
            
    elif choice == 4:
        clear_specific_addon_cache()

def clear_specific_addon_cache():
    """Clear cache for a specific addon"""
    dialog = xbmcgui.Dialog()
    
    addon_list = []
    addon_sizes = []
    
    if os.path.exists(KODI_ADDON_DATA):
        for addon in os.listdir(KODI_ADDON_DATA):
            addon_path = os.path.join(KODI_ADDON_DATA, addon)
            size = get_size(addon_path)
            if size > 0.1:  # Only show addons with >0.1 MB
                addon_list.append(addon)
                addon_sizes.append(size)
    
    if not addon_list:
        dialog.ok("No Data", "No addon data found")
        return
    
    # Sort by size
    combined = sorted(zip(addon_sizes, addon_list), reverse=True)
    display_list = [f"{name} ({size:.1f} MB)" for size, name in combined]
    
    choice = dialog.select("Select Addon", display_list)
    if choice >= 0:
        addon_name = combined[choice][1]
        addon_path = os.path.join(KODI_ADDON_DATA, addon_name)
        
        sub_choice = dialog.select(f"Clear {addon_name}", [
            "Clear Cache Only",
            "Clear ALL Addon Data"
        ])
        
        if sub_choice == 0:
            for cache_name in ['cache', 'Cache', 'temp', 'Temp']:
                cache_path = os.path.join(addon_path, cache_name)
                if os.path.exists(cache_path):
                    shutil.rmtree(cache_path)
            notify("Cache", f"Cache cleared for {addon_name}")
            
        elif sub_choice == 1:
            if dialog.yesno("Warning", f"Delete ALL data for {addon_name}?"):
                shutil.rmtree(addon_path)
                notify("Cache", f"All data cleared for {addon_name}")

# ============================================
# CLEAR PACKAGES
# ============================================
def clear_packages():
    """Clear downloaded addon packages"""
    dialog = xbmcgui.Dialog()
    
    pkg_size = get_size(KODI_PACKAGES)
    pkg_count = 0
    
    if os.path.exists(KODI_PACKAGES):
        pkg_count = len([f for f in os.listdir(KODI_PACKAGES) if f.endswith('.zip')])
    
    choice = dialog.select("Clear Packages", [
        f"View Package Info ({pkg_count} files, {pkg_size:.1f} MB)",
        "Clear All Packages",
        "Clear Old Packages (Keep Latest)"
    ])
    
    if choice == 0:
        dialog.ok("Package Info",
                  f"Total Packages: {pkg_count}\nTotal Size: {pkg_size:.1f} MB\nLocation: {KODI_PACKAGES}")
                  
    elif choice == 1:
        if dialog.yesno("Confirm", f"Delete ALL {pkg_count} packages ({pkg_size:.1f} MB)?"):
            deleted = delete_folder_contents(KODI_PACKAGES, ['.zip'])
            dialog.ok("Packages Cleared", f"Deleted {deleted} package files")
            
    elif choice == 2:
        if not os.path.exists(KODI_PACKAGES):
            dialog.ok("No Packages", "Package folder not found")
            return
            
        # Keep only most recent version of each package
        packages = {}
        for f in os.listdir(KODI_PACKAGES):
            if f.endswith('.zip'):
                # Extract addon name (everything before version number)
                parts = f.rsplit('-', 1)
                if len(parts) == 2:
                    name = parts[0]
                    if name not in packages:
                        packages[name] = []
                    packages[name].append(f)
        
        deleted = 0
        for name, files in packages.items():
            if len(files) > 1:
                # Sort by modification time, keep newest
                files_with_time = [(f, os.path.getmtime(os.path.join(KODI_PACKAGES, f))) for f in files]
                files_with_time.sort(key=lambda x: x[1], reverse=True)
                
                # Delete all but newest
                for f, _ in files_with_time[1:]:
                    try:
                        os.remove(os.path.join(KODI_PACKAGES, f))
                        deleted += 1
                    except:
                        pass
        
        dialog.ok("Old Packages Cleared", f"Deleted {deleted} old package(s)")

# ============================================
# LOG UPLOADER / VIEWER
# ============================================
def log_uploader_menu():
    """Log Uploader Menu - View and upload Kodi logs"""
    dialog = xbmcgui.Dialog()
    
    # Kodi log paths
    log_path = xbmcvfs.translatePath('special://logpath/kodi.log')
    old_log_path = xbmcvfs.translatePath('special://logpath/kodi.old.log')
    
    choice = dialog.select("Log Uploader", [
        "View Current Log (kodi.log)",
        "View Previous Log (kodi.old.log)",
        "Upload Log to Pastebin",
        "Upload Log to paste.kodi.tv",
        "Copy Log Path to Clipboard",
        "Log File Info"
    ])
    
    if choice == 0:
        view_log_fullscreen(log_path, "Current Kodi Log")
    elif choice == 1:
        view_log_fullscreen(old_log_path, "Previous Kodi Log")
    elif choice == 2:
        upload_log_to_pastebin(log_path)
    elif choice == 3:
        upload_log_to_kodi_paste(log_path)
    elif choice == 4:
        copy_log_path(log_path)
    elif choice == 5:
        show_log_info(log_path, old_log_path)


def view_log_fullscreen(log_path, title="Kodi Log"):
    """View log file in fullscreen with syntax highlighting"""
    dialog = xbmcgui.Dialog()
    
    if not xbmcvfs.exists(log_path):
        dialog.ok("Log Not Found", f"Log file not found:\n{log_path}")
        return
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Get last portion if too large (Kodi textviewer has limits)
        max_chars = 100000
        if len(content) > max_chars:
            content = f"... [Showing last {max_chars} characters] ...\n\n" + content[-max_chars:]
        
        # Apply simple syntax highlighting with Kodi color tags
        highlighted = apply_log_highlighting(content)
        
        dialog.textviewer(title, highlighted)
        
    except Exception as e:
        dialog.ok("Error Reading Log", f"Could not read log file:\n{str(e)}")


def apply_log_highlighting(content):
    """Apply syntax highlighting to log content using Kodi color tags"""
    lines = content.split('\n')
    highlighted_lines = []
    
    for line in lines:
        # Error lines - red
        if 'ERROR' in line.upper() or 'EXCEPTION' in line.upper():
            highlighted_lines.append(f'[COLOR red]{line}[/COLOR]')
        # Warning lines - orange
        elif 'WARNING' in line.upper() or 'WARN' in line.upper():
            highlighted_lines.append(f'[COLOR orange]{line}[/COLOR]')
        # Debug lines - gray
        elif 'DEBUG' in line.upper():
            highlighted_lines.append(f'[COLOR gray]{line}[/COLOR]')
        # Info lines - cyan (matching theme)
        elif 'INFO' in line.upper():
            highlighted_lines.append(f'[COLOR cyan]{line}[/COLOR]')
        # Notice lines - yellow
        elif 'NOTICE' in line.upper():
            highlighted_lines.append(f'[COLOR yellow]{line}[/COLOR]')
        # Timestamps - slightly dimmed
        elif line.startswith('20') and ':' in line[:20]:
            highlighted_lines.append(f'[COLOR lightgray]{line}[/COLOR]')
        else:
            highlighted_lines.append(line)
    
    return '\n'.join(highlighted_lines)


def upload_log_to_pastebin(log_path):
    """Upload log to dpaste.com (no API key required)"""
    dialog = xbmcgui.Dialog()
    
    if not xbmcvfs.exists(log_path):
        dialog.ok("Log Not Found", "Log file not found.")
        return
    
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("Uploading Log", "Reading log file...")
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Limit size for upload
        max_size = 500000  # 500KB limit
        if len(content) > max_size:
            content = content[-max_size:]
            content = "... [Truncated - showing last 500KB] ...\n\n" + content
        
        pDialog.update(50, "Uploading to dpaste.com...")
        
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        # Use dpaste.com API
        data = urllib.parse.urlencode({
            'content': content,
            'syntax': 'text',
            'expiry_days': 7
        }).encode('utf-8')
        
        req = urllib.request.Request(
            'https://dpaste.com/api/v2/',
            data=data,
            headers={'User-Agent': 'TheAccountant/4.3'}
        )
        
        response = urllib.request.urlopen(req, context=ctx, timeout=30)
        paste_url = response.read().decode('utf-8').strip()
        
        pDialog.close()
        
        dialog.ok("Upload Complete", f"Log uploaded successfully!\n\nURL: {paste_url}\n\nShare this URL for support.")
        
        # Try to copy to clipboard
        try:
            xbmc.executebuiltin(f'SetProperty(clipboard,{paste_url},10000)')
        except:
            pass
            
    except Exception as e:
        pDialog.close()
        dialog.ok("Upload Failed", f"Could not upload log:\n{str(e)}")


def upload_log_to_kodi_paste(log_path):
    """Upload log to paste.kodi.tv"""
    dialog = xbmcgui.Dialog()
    
    if not xbmcvfs.exists(log_path):
        dialog.ok("Log Not Found", "Log file not found.")
        return
    
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("Uploading Log", "Reading log file...")
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Limit size
        max_size = 500000
        if len(content) > max_size:
            content = content[-max_size:]
        
        pDialog.update(50, "Uploading to paste.kodi.tv...")
        
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        # paste.kodi.tv uses POST
        data = urllib.parse.urlencode({
            'paste_data': content,
            'api_submit': 'true',
            'paste_lang': 'kodi'
        }).encode('utf-8')
        
        req = urllib.request.Request(
            'https://paste.kodi.tv/',
            data=data,
            headers={'User-Agent': 'TheAccountant/4.3'}
        )
        
        response = urllib.request.urlopen(req, context=ctx, timeout=30)
        result = response.read().decode('utf-8')
        
        pDialog.close()
        
        # Parse response for URL
        if 'paste.kodi.tv' in result or result.startswith('http'):
            paste_url = result.strip() if result.startswith('http') else f"https://paste.kodi.tv/{result.strip()}"
            dialog.ok("Upload Complete", f"Log uploaded successfully!\n\nURL: {paste_url}")
        else:
            dialog.ok("Upload Result", f"Server response:\n{result[:500]}")
            
    except Exception as e:
        pDialog.close()
        dialog.ok("Upload Failed", f"Could not upload log:\n{str(e)}\n\nTry using dpaste.com instead.")


def copy_log_path(log_path):
    """Copy log path to clipboard / show path"""
    dialog = xbmcgui.Dialog()
    dialog.ok("Log File Path", f"Kodi Log Location:\n\n{log_path}\n\nUse a file manager to access this file.")


def show_log_info(log_path, old_log_path):
    """Show information about log files"""
    dialog = xbmcgui.Dialog()
    
    info_lines = ["[COLOR cyan]LOG FILE INFORMATION[/COLOR]\n"]
    
    for path, name in [(log_path, "Current Log (kodi.log)"), (old_log_path, "Previous Log (kodi.old.log)")]:
        info_lines.append(f"[COLOR yellow]{name}[/COLOR]")
        if xbmcvfs.exists(path):
            try:
                size = os.path.getsize(path)
                mtime = os.path.getmtime(path)
                info_lines.append(f"  Path: {path}")
                info_lines.append(f"  Size: {size / 1024:.1f} KB")
                info_lines.append(f"  Modified: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}")
                
                # Count errors/warnings
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    error_count = content.upper().count('ERROR')
                    warning_count = content.upper().count('WARNING')
                    info_lines.append(f"  Errors: [COLOR red]{error_count}[/COLOR]")
                    info_lines.append(f"  Warnings: [COLOR orange]{warning_count}[/COLOR]")
                except:
                    pass
            except:
                info_lines.append(f"  Path: {path}")
                info_lines.append("  Could not read file info")
        else:
            info_lines.append(f"  [COLOR gray]File not found[/COLOR]")
        info_lines.append("")
    
    dialog.textviewer("Log Information", '\n'.join(info_lines))


# ============================================
# HELP / GUIDE
# ============================================
def help_menu():
    """Help and guide section"""
    dialog = xbmcgui.Dialog()
    
    choice = dialog.select("Help & Guide", [
        "About The Accountant",
        "Speed Optimizer Guide",
        "Authentication Setup Guide",
        "Backup & Restore Guide",
        "Troubleshooting",
        "Credits"
    ])
    
    if choice == 0:
        dialog.ok("About The Accountant",
                  "Version: 4.0.3\nAuthor: zeus768\nMaster Pro Suite for Kodi maintenance")
                  
    elif choice == 1:
        dialog.ok("Speed Optimizer",
                  "Clears temp files, old thumbnails, and packages.\nRun weekly for best performance.\nRestart Kodi after optimization.")
                  
    elif choice == 2:
        dialog.ok("Authentication Setup",
                  "1. Enter your API keys/tokens in Auth menu\n2. Use 'Sync All' to push to addons\n3. Credentials are stored securely in vault")
                  
    elif choice == 3:
        dialog.ok("Backup & Restore",
                  "USB Backup: Export/import vault to USB drive\nFavourites Vault: Backup your Kodi favourites\nOne-Click Restore: Restore all saved data")
                  
    elif choice == 4:
        dialog.ok("Troubleshooting",
                  "Addons not working? Try 'Repair Video Addons'\nSlow performance? Run 'Speed Optimizer'\nLost settings? Use 'One-Click Restore'")
                  
    elif choice == 5:
        dialog.ok("Credits",
                  "The Accountant by zeus768\nMaster Pro Suite v4.0.3\nThank you for using this addon!")

# ============================================
# INTERNET SPEED TESTER
# ============================================
def speed_test_menu():
    """Internet Speed Test Menu"""
    dialog = xbmcgui.Dialog()
    
    choice = dialog.select("Internet Speed Tester", [
        "Real-Time Speed Test (Animated Gauge)",
        "Run Full Speed Test (Download + Upload + Ping)",
        "Quick Download Test Only",
        "Quick Upload Test Only",
        "Ping Test Only",
        "View Last Test Results",
        "Speed Test Settings"
    ])
    
    if choice == 0:
        # New animated speedometer window
        from resources.lib.speed_test_window import show_speed_test_window
        show_speed_test_window()
    elif choice == 1:
        run_full_speed_test()
    elif choice == 2:
        run_download_test()
    elif choice == 3:
        run_upload_test()
    elif choice == 4:
        run_ping_test()
    elif choice == 5:
        view_speed_results()
    elif choice == 6:
        speed_test_settings()

def run_full_speed_test():
    """Run complete speed test"""
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("Internet Speed Test", "Initializing...")
    
    results = {
        'ping': 0,
        'download': 0,
        'upload': 0,
        'server': 'Unknown',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    try:
        import urllib.request
        import urllib.error
        import ssl
        
        # Create SSL context that doesn't verify (for compatibility)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        # Test servers - using fast.com CDN and other reliable endpoints
        test_urls = [
            ('https://speed.cloudflare.com/__down?bytes=10000000', 'Cloudflare'),
            ('https://proof.ovh.net/files/1Mb.dat', 'OVH Europe'),
            ('http://speedtest.tele2.net/1MB.zip', 'Tele2'),
        ]
        
        # Step 1: Ping Test
        pDialog.update(10, "Testing ping latency...")
        ping_times = []
        ping_url = 'https://www.google.com'
        
        for i in range(3):
            try:
                start = time.time()
                req = urllib.request.Request(ping_url, headers={'User-Agent': 'Mozilla/5.0'})
                urllib.request.urlopen(req, timeout=5, context=ctx)
                ping_times.append((time.time() - start) * 1000)
            except:
                pass
        
        if ping_times:
            results['ping'] = sum(ping_times) / len(ping_times)
        
        if pDialog.iscanceled():
            pDialog.close()
            return
        
        # Step 2: Download Test
        pDialog.update(30, "Testing download speed...")
        download_speeds = []
        
        for url, server_name in test_urls:
            if pDialog.iscanceled():
                break
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                start = time.time()
                response = urllib.request.urlopen(req, timeout=15, context=ctx)
                data = response.read()
                elapsed = time.time() - start
                
                if elapsed > 0:
                    speed_mbps = (len(data) * 8) / (elapsed * 1000000)
                    download_speeds.append((speed_mbps, server_name))
                    pDialog.update(50, f"Download: {speed_mbps:.2f} Mbps ({server_name})")
            except Exception as e:
                xbmc.log(f'[Accountant] Speed test download error: {e}', xbmc.LOGDEBUG)
                pass
        
        if download_speeds:
            best_download = max(download_speeds, key=lambda x: x[0])
            results['download'] = best_download[0]
            results['server'] = best_download[1]
        
        if pDialog.iscanceled():
            pDialog.close()
            return
        
        # Step 3: Upload Test (using POST to httpbin)
        pDialog.update(70, "Testing upload speed...")
        try:
            # Generate random data for upload test
            test_data = b'x' * 500000  # 500KB test data
            
            upload_url = 'https://httpbin.org/post'
            req = urllib.request.Request(upload_url, data=test_data, 
                                         headers={'User-Agent': 'Mozilla/5.0', 
                                                  'Content-Type': 'application/octet-stream'})
            
            start = time.time()
            response = urllib.request.urlopen(req, timeout=30, context=ctx)
            response.read()
            elapsed = time.time() - start
            
            if elapsed > 0:
                results['upload'] = (len(test_data) * 8) / (elapsed * 1000000)
        except Exception as e:
            xbmc.log(f'[Accountant] Speed test upload error: {e}', xbmc.LOGDEBUG)
            results['upload'] = 0
        
        pDialog.update(90, "Saving results...")
        
        # Save results
        save_speed_results(results)
        
        pDialog.close()
        
        # Show results
        dialog = xbmcgui.Dialog()
        result_text = (f"[COLOR cyan]SPEED TEST RESULTS[/COLOR]\n\n"
                      f"[COLOR yellow]Ping:[/COLOR] {results['ping']:.0f} ms\n"
                      f"[COLOR green]Download:[/COLOR] {results['download']:.2f} Mbps\n"
                      f"[COLOR orange]Upload:[/COLOR] {results['upload']:.2f} Mbps\n\n"
                      f"Server: {results['server']}\n"
                      f"Time: {results['timestamp']}")
        
        dialog.textviewer("Speed Test Complete", result_text)
        
    except Exception as e:
        pDialog.close()
        xbmc.log(f'[Accountant] Speed test error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Speed Test Failed", f"Error: {str(e)}")

def run_download_test():
    """Quick download test only"""
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("Download Speed Test", "Testing download speed...")
    
    try:
        import urllib.request
        import ssl
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        test_url = 'https://speed.cloudflare.com/__down?bytes=10000000'
        req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
        
        start = time.time()
        response = urllib.request.urlopen(req, timeout=30, context=ctx)
        data = response.read()
        elapsed = time.time() - start
        
        pDialog.close()
        
        if elapsed > 0:
            speed_mbps = (len(data) * 8) / (elapsed * 1000000)
            xbmcgui.Dialog().ok("Download Test Complete", 
                               f"Download Speed: {speed_mbps:.2f} Mbps\nData: {len(data)/1000000:.1f} MB in {elapsed:.1f}s")
        else:
            xbmcgui.Dialog().ok("Download Test", "Could not calculate speed")
            
    except Exception as e:
        pDialog.close()
        xbmcgui.Dialog().ok("Download Test Failed", f"Error: {str(e)}")

def run_upload_test():
    """Quick upload test only"""
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("Upload Speed Test", "Testing upload speed...")
    
    try:
        import urllib.request
        import ssl
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        test_data = b'x' * 500000
        upload_url = 'https://httpbin.org/post'
        req = urllib.request.Request(upload_url, data=test_data,
                                     headers={'User-Agent': 'Mozilla/5.0',
                                              'Content-Type': 'application/octet-stream'})
        
        start = time.time()
        response = urllib.request.urlopen(req, timeout=30, context=ctx)
        response.read()
        elapsed = time.time() - start
        
        pDialog.close()
        
        if elapsed > 0:
            speed_mbps = (len(test_data) * 8) / (elapsed * 1000000)
            xbmcgui.Dialog().ok("Upload Test Complete",
                               f"Upload Speed: {speed_mbps:.2f} Mbps\nData: {len(test_data)/1000:.0f} KB in {elapsed:.1f}s")
        else:
            xbmcgui.Dialog().ok("Upload Test", "Could not calculate speed")
            
    except Exception as e:
        pDialog.close()
        xbmcgui.Dialog().ok("Upload Test Failed", f"Error: {str(e)}")

def run_ping_test():
    """Quick ping test only"""
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("Ping Test", "Testing network latency...")
    
    try:
        import urllib.request
        import ssl
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        test_hosts = [
            ('https://www.google.com', 'Google'),
            ('https://www.cloudflare.com', 'Cloudflare'),
            ('https://www.amazon.com', 'Amazon'),
        ]
        
        results = []
        for i, (url, name) in enumerate(test_hosts):
            pDialog.update(int((i/len(test_hosts))*100), f"Pinging {name}...")
            ping_times = []
            
            for _ in range(3):
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    start = time.time()
                    urllib.request.urlopen(req, timeout=5, context=ctx)
                    ping_times.append((time.time() - start) * 1000)
                except:
                    pass
            
            if ping_times:
                avg = sum(ping_times) / len(ping_times)
                results.append(f"{name}: {avg:.0f} ms")
        
        pDialog.close()
        
        if results:
            xbmcgui.Dialog().ok("Ping Test Complete", "\n".join(results))
        else:
            xbmcgui.Dialog().ok("Ping Test", "Could not reach any servers")
            
    except Exception as e:
        pDialog.close()
        xbmcgui.Dialog().ok("Ping Test Failed", f"Error: {str(e)}")

def save_speed_results(results):
    """Save speed test results to vault"""
    vault = load_vault()
    
    if 'speed_history' not in vault:
        vault['speed_history'] = []
    
    vault['speed_history'].insert(0, results)
    vault['speed_history'] = vault['speed_history'][:10]  # Keep last 10 results
    vault['last_speed_test'] = results
    
    save_vault(vault)

def view_speed_results():
    """View historical speed test results"""
    vault = load_vault()
    history = vault.get('speed_history', [])
    
    if not history:
        xbmcgui.Dialog().ok("Speed Test History", "No speed tests recorded yet.\nRun a speed test first!")
        return
    
    lines = ["[COLOR cyan]SPEED TEST HISTORY[/COLOR]\n"]
    for i, result in enumerate(history):
        lines.append(f"[COLOR yellow]Test {i+1}:[/COLOR] {result.get('timestamp', 'Unknown')}")
        lines.append(f"  Ping: {result.get('ping', 0):.0f} ms")
        lines.append(f"  Download: {result.get('download', 0):.2f} Mbps")
        lines.append(f"  Upload: {result.get('upload', 0):.2f} Mbps")
        lines.append(f"  Server: {result.get('server', 'Unknown')}")
        lines.append("")
    
    xbmcgui.Dialog().textviewer("Speed Test History", "\n".join(lines))

def speed_test_settings():
    """Speed test configuration"""
    dialog = xbmcgui.Dialog()
    vault = load_vault()
    
    current_size = vault.get('speedtest_size', 'medium')
    
    choice = dialog.select("Speed Test Settings", [
        f"Test Data Size: {current_size.upper()}",
        "Set to Small (1MB - Fast)",
        "Set to Medium (10MB - Balanced)",
        "Set to Large (25MB - Accurate)",
        "Clear Speed Test History"
    ])
    
    if choice == 1:
        vault['speedtest_size'] = 'small'
        save_vault(vault)
        notify("Speed Test", "Test size set to Small")
    elif choice == 2:
        vault['speedtest_size'] = 'medium'
        save_vault(vault)
        notify("Speed Test", "Test size set to Medium")
    elif choice == 3:
        vault['speedtest_size'] = 'large'
        save_vault(vault)
        notify("Speed Test", "Test size set to Large")
    elif choice == 4:
        if dialog.yesno("Clear History", "Delete all speed test history?"):
            vault.pop('speed_history', None)
            vault.pop('last_speed_test', None)
            save_vault(vault)
            notify("Speed Test", "History cleared")

# ============================================
# SCHEDULED AUTO-CLEAN
# ============================================
def auto_clean_settings():
    """Configure automatic cleaning on startup"""
    dialog = xbmcgui.Dialog()
    vault = load_vault()
    
    current_setting = vault.get('auto_clean', 'disabled')
    last_clean = vault.get('last_auto_clean', 'Never')
    
    choice = dialog.select("Scheduled Auto-Clean", [
        f"Current: {current_setting.upper()}",
        f"Last Clean: {last_clean}",
        "---",
        "Enable: Clean on Every Startup",
        "Enable: Clean Once Per Day",
        "Enable: Clean Once Per Week",
        "Disable Auto-Clean",
        "Run Clean Now"
    ])
    
    if choice == 3:
        vault['auto_clean'] = 'startup'
        save_vault(vault)
        notify("Auto-Clean", "Enabled: Every Startup")
    elif choice == 4:
        vault['auto_clean'] = 'daily'
        save_vault(vault)
        notify("Auto-Clean", "Enabled: Once Per Day")
    elif choice == 5:
        vault['auto_clean'] = 'weekly'
        save_vault(vault)
        notify("Auto-Clean", "Enabled: Once Per Week")
    elif choice == 6:
        vault['auto_clean'] = 'disabled'
        save_vault(vault)
        notify("Auto-Clean", "Disabled")
    elif choice == 7:
        run_auto_clean(force=True)

def run_auto_clean(force=False):
    """Run automatic cleaning based on settings"""
    vault = load_vault()
    setting = vault.get('auto_clean', 'disabled')
    
    if setting == 'disabled' and not force:
        return
    
    last_clean = vault.get('last_auto_clean_time', 0)
    current_time = time.time()
    
    # Check if we should run based on schedule
    should_run = force
    if not force:
        if setting == 'startup':
            should_run = True
        elif setting == 'daily':
            should_run = (current_time - last_clean) > 86400  # 24 hours
        elif setting == 'weekly':
            should_run = (current_time - last_clean) > 604800  # 7 days
    
    if should_run:
        # Silent clean - no dialogs
        delete_folder_contents(KODI_TEMP)
        delete_folder_contents(KODI_PACKAGES, ['.zip'])
        
        # Update last clean time
        vault['last_auto_clean_time'] = current_time
        vault['last_auto_clean'] = time.strftime('%Y-%m-%d %H:%M')
        save_vault(vault)
        
        notify("Auto-Clean", "System optimized!")

def check_auto_clean_on_startup():
    """Check and run auto-clean on addon startup"""
    try:
        vault = load_vault()
        if vault.get('auto_clean', 'disabled') != 'disabled':
            run_auto_clean()
    except:
        pass


# ============================================
# SAVE MY BUILD (Build Creator / Zip Exporter)
# ============================================
def save_my_build():
    """Build Creator - zip up a Kodi build (addons + userdata) and save to device."""
    import zipfile
    dialog = xbmcgui.Dialog()

    # --- Mode selection: Quick full vs Custom ---
    mode = dialog.select("Save My Build", [
        "Quick Build (addons + userdata)",
        "Custom Build (choose what to include)",
        "About Save My Build"
    ])
    if mode < 0:
        return
    if mode == 2:
        dialog.ok("Save My Build",
                  "Package your current Kodi setup into a portable .zip build.\n\n"
                  "Quick: addons + userdata (skin settings, sources, favourites, keymaps)\n"
                  "Custom: pick exactly which sections to include\n\n"
                  "Saved zip can be restored on any Kodi device.")
        return

    # --- Define build sections (label, source path, arcname inside zip) ---
    sections = [
        ("Addons",                KODI_ADDONS,                           "addons"),
        ("Addon Data (settings)", KODI_ADDON_DATA,                       "userdata/addon_data"),
        ("Favourites",            FAV_FILE,                              "userdata/favourites.xml"),
        ("Sources",               os.path.join(KODI_USERDATA, 'sources.xml'),  "userdata/sources.xml"),
        ("Profiles",              os.path.join(KODI_USERDATA, 'profiles.xml'), "userdata/profiles.xml"),
        ("Keymaps",               os.path.join(KODI_USERDATA, 'keymaps'),      "userdata/keymaps"),
        ("GUI Settings",          os.path.join(KODI_USERDATA, 'guisettings.xml'), "userdata/guisettings.xml"),
        ("Advanced Settings",     os.path.join(KODI_USERDATA, 'advancedsettings.xml'), "userdata/advancedsettings.xml"),
        ("Player Core Factory",   os.path.join(KODI_USERDATA, 'playercorefactory.xml'), "userdata/playercorefactory.xml"),
    ]

    if mode == 0:  # Quick
        selected_idx = list(range(len(sections)))
    else:  # Custom
        preselected = [True] * len(sections)
        picked = dialog.multiselect("Select what to include in build",
                                    [s[0] for s in sections],
                                    preselect=[i for i, v in enumerate(preselected) if v])
        if not picked:
            return
        selected_idx = picked

    # --- Build name ---
    default_name = f"MyBuild_{time.strftime('%Y-%m-%d_%H%M')}"
    build_name = dialog.input("Name your build (no extension)", default_name)
    if not build_name:
        return
    # sanitize
    safe_name = "".join(c for c in build_name if c.isalnum() or c in "-_ .").strip().replace(" ", "_")
    if not safe_name:
        safe_name = default_name
    zip_filename = safe_name + ".zip"

    # --- Build Info banner (creator name + note, remembered in vault) ---
    vault = load_vault()
    last_creator = vault.get('build_creator', '')
    creator = dialog.input("Creator name (shown in build info)", last_creator)
    if creator is None:
        creator = ''
    note = dialog.input("Build note / description (optional)", "")
    if note is None:
        note = ''
    if creator and creator != last_creator:
        vault['build_creator'] = creator
        save_vault(vault)

    # --- Save destination: default OR browse ---
    default_dest = os.path.join(KODI_HOME, 'build_exports')
    dest_choice = dialog.select("Save location", [
        f"Default folder ({default_dest})",
        "Browse... (pick any folder on device)"
    ])
    if dest_choice < 0:
        return
    if dest_choice == 0:
        dest_dir = default_dest
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except Exception as e:
            dialog.ok("Save My Build", f"Could not create default folder:\n{e}")
            return
    else:
        dest_dir = dialog.browse(0, 'Select Save Folder', 'files')
        if not dest_dir:
            return

    zip_path = os.path.join(dest_dir, zip_filename)

    # --- Confirm if overwriting ---
    if os.path.exists(zip_path):
        if not dialog.yesno("Save My Build", f"{zip_filename} already exists.\nOverwrite?"):
            return

    # --- Build the zip ---
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("Save My Build", "Preparing build...")

    # Paths to skip (avoid recursion & bloat)
    skip_dirs = {
        os.path.normpath(KODI_PACKAGES),
        os.path.normpath(KODI_THUMBNAILS),
        os.path.normpath(KODI_TEMP),
    }
    skip_names = {'cache', 'Cache', 'temp', 'Temp', 'tmp', 'Thumbnails', 'packages'}

    total = len(selected_idx)
    added_files = 0
    added_bytes = 0

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            for i, idx in enumerate(selected_idx):
                label, src, arc = sections[idx]
                pct = int((i / max(total, 1)) * 100)
                pDialog.update(pct, f"Adding: {label}")
                if pDialog.iscanceled():
                    raise RuntimeError("Cancelled by user")

                if not os.path.exists(src):
                    continue

                if os.path.isfile(src):
                    try:
                        zf.write(src, arc)
                        added_files += 1
                        added_bytes += os.path.getsize(src)
                    except:
                        pass
                    continue

                # Directory: walk
                src_norm = os.path.normpath(src)
                for root, dirs, files in os.walk(src):
                    # Filter junk subdirs in-place
                    dirs[:] = [d for d in dirs
                               if d not in skip_names
                               and os.path.normpath(os.path.join(root, d)) not in skip_dirs]
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            rel = os.path.relpath(fp, src_norm)
                            zf.write(fp, os.path.join(arc, rel))
                            added_files += 1
                            added_bytes += os.path.getsize(fp)
                        except:
                            pass
                    if pDialog.iscanceled():
                        raise RuntimeError("Cancelled by user")

            # Write a manifest
            manifest = {
                "build_name": safe_name,
                "creator": creator,
                "note": note,
                "created": time.strftime('%Y-%m-%d %H:%M:%S'),
                "created_epoch": int(time.time()),
                "created_by": "The Accountant - Save My Build",
                "addon_version": ADDON.getAddonInfo('version'),
                "sections": [sections[i][0] for i in selected_idx],
                "files": added_files,
                "size_bytes": added_bytes
            }
            zf.writestr("build_manifest.json", json.dumps(manifest, indent=2))

            # Human-readable banner
            banner = (
                "============================================\n"
                f"  {safe_name}\n"
                "============================================\n"
                f"Creator   : {creator or 'Unknown'}\n"
                f"Created   : {manifest['created']}\n"
                f"Built with: The Accountant v{manifest['addon_version']}\n"
                f"Sections  : {', '.join(manifest['sections'])}\n"
                f"Files     : {added_files}\n"
                f"Size      : {added_bytes / (1024*1024):.1f} MB\n"
            )
            if note:
                banner += f"\nNote:\n{note}\n"
            zf.writestr("build_info.txt", banner)

        pDialog.close()
        size_mb = added_bytes / (1024 * 1024)
        dialog.ok("Build Saved",
                  f"[COLOR cyan]{zip_filename}[/COLOR]\n"
                  f"Creator: {creator or 'Unknown'}\n"
                  f"Location: {dest_dir}\n"
                  f"Files: {added_files}\n"
                  f"Size: {size_mb:.1f} MB")
    except Exception as e:
        try:
            pDialog.close()
        except:
            pass
        # Clean up partial zip
        try:
            if os.path.exists(zip_path):
                os.remove(zip_path)
        except:
            pass
        dialog.ok("Save My Build Failed", f"Error: {str(e)}")


# ============================================
# MAIN MENU
# ============================================

def refresh_widgets():
    """Force refresh all Kodi widgets and containers"""
    try:
        xbmc.executebuiltin('UpdateLibrary(video)')
        xbmc.sleep(500)
        xbmc.executebuiltin('UpdateLibrary(music)')
        xbmc.sleep(500)
        xbmc.executebuiltin('Container.Refresh')
        xbmc.sleep(500)
        xbmc.executebuiltin('ReloadSkin()')
        notify("Widgets Refreshed", "All widgets and containers updated")
    except Exception as e:
        xbmc.log(f'[Accountant] Widget refresh error: {e}', xbmc.LOGERROR)
        notify("Error", f"Refresh failed: {e}")


def main_menu():
    """Main menu display"""
    items = [
        ("ONE-CLICK SPEED OPTIMIZER", "speed", "speed.png"),
        ("SCHEDULED AUTO-CLEAN", "autoclean", "autoclean.png"),
        ("--- Network & Connectivity ---", "spacer", ""),
        ("INTERNET SPEED TESTER", "speedtest", "speedtest.png"),
        ("--- Account Management ---", "spacer", ""),
        ("Pair RD / Trakt / Auth / PM / AD / TMDB", "auth", "auth.png"),
        ("VIEW ACCOUNT CARDS", "account_cards", "auth.png"),
        ("SYNC ALL TO ADDONS", "sync_all", "sync.png"),
        ("--- Backup & Restore ---", "spacer", ""),
        ("IPTV Login Vault", "iptv", "iptv.png"),
        ("Favourites Vault", "favs", "favs.png"),
        ("USB BACKUP TOOL", "usb", "usb.png"),
        ("SAVE MY BUILD", "save_build", "build.png"),
        ("BUILD WIZARD CREATOR", "wizard_creator", "build.png"),
        ("ONE-CLICK RESTORE (ALL)", "restore", "restore.png"),
        ("--- Maintenance Tools ---", "spacer", ""),
        ("REFRESH WIDGETS", "refresh_widgets", "refresh.png"),
        ("REPAIR VIDEO ADDONS", "repair", "repair.png"),
        ("CLEAR CACHE (MANUAL)", "clean", "clean.png"),
        ("CLEAR PACKAGES", "packages", "packages.png"),
        ("LOG UPLOADER", "log_uploader", "log.png"),
        ("--- Help & Info ---", "spacer", ""),
        ("HELP / GUIDE", "help", "help.png"),
        ("Buy Me a Beer", "buy_beer", "")
    ]
    
    for label, act, icon in items:
        li = xbmcgui.ListItem(label=label)
        
        if act == "spacer":
            li.setArt({'icon': ADDON_ICON, 'thumb': ADDON_ICON, 'fanart': ADDON_FANART})
            xbmcplugin.addDirectoryItem(HANDLE, "", li, False)
        else:
            art = get_art(icon)
            li.setArt({'icon': art, 'thumb': art, 'fanart': ADDON_FANART})
            url = f"{sys.argv[0]}?action={act}"
            is_folder = act in ['auth']
            xbmcplugin.addDirectoryItem(HANDLE, url, li, is_folder)
    
    xbmcplugin.endOfDirectory(HANDLE)

# ============================================
# BUILD WIZARD CREATOR
# ============================================
def build_wizard_menu():
    import hashlib
    d = xbmcgui.Dialog()
    exports = os.path.join(KODI_HOME, 'build_exports')
    os.makedirs(exports, exist_ok=True)
    c = d.select("Build Wizard Creator", [
        "Manage Builds (list / rename / delete)",
        "Wizard Settings (GitHub user, repo, author)",
        "Generate wizard.xml for a build",
        "Generate Repo Scaffold (ready to upload)",
        "Generate Companion Wizard Addon (.zip)",
        "How To Publish on GitHub (instructions)",
    ])
    if c == 0: bwc_manage(exports)
    elif c == 1: bwc_settings()
    elif c == 2: bwc_gen_xml(exports)
    elif c == 3: bwc_scaffold(exports)
    elif c == 4: bwc_gen_wizard_addon(exports)
    elif c == 5: bwc_instructions()

def bwc_manage(exports):
    d = xbmcgui.Dialog()
    zips = sorted([f for f in os.listdir(exports) if f.endswith('.zip')])
    if not zips:
        d.ok("Build Manager", "No builds yet. Use SAVE MY BUILD first.")
        return
    labels = [f"{z} ({os.path.getsize(os.path.join(exports, z))/1048576:.1f} MB)" for z in zips]
    i = d.select("Select a build", labels)
    if i < 0: return
    path = os.path.join(exports, zips[i])
    act = d.select(zips[i], ["Rename", "Delete", "Duplicate", "Show path", "View build_info.txt"])
    if act == 0:
        n = d.input("New name (no extension)", zips[i][:-4])
        if n:
            os.rename(path, os.path.join(exports, n + ".zip"))
            notify("Builds", "Renamed")
    elif act == 1:
        if d.yesno("Delete", f"Delete {zips[i]}?"):
            os.remove(path); notify("Builds", "Deleted")
    elif act == 2:
        shutil.copy2(path, os.path.join(exports, zips[i][:-4] + "_copy.zip"))
        notify("Builds", "Duplicated")
    elif act == 3:
        d.ok("Path", path)
    elif act == 4:
        import zipfile
        try:
            with zipfile.ZipFile(path) as zf:
                d.textviewer("build_info.txt", zf.read("build_info.txt").decode('utf-8', 'ignore'))
        except Exception as e:
            d.ok("Error", str(e))

def bwc_settings():
    d = xbmcgui.Dialog(); v = load_vault(); ws = v.get('wizard_settings', {})
    fields = [("gh_user", "GitHub username"), ("gh_repo", "Repo name"),
              ("author", "Build author display name"),
              ("addon_id", "Wizard addon id (e.g. program.yourname.wizard)"),
              ("icon_url", "Icon URL (optional)"), ("fanart_url", "Fanart URL (optional)"),
              ("support_url", "Support URL (optional)")]
    while True:
        labels = []
        for k, lbl in fields:
            val = ws.get(k, '')
            labels.append(f"{lbl}: {val if val else '(not set)'}")
        pages_url = f"https://{ws.get('gh_user','<user>')}.github.io/{ws.get('gh_repo','<repo>')}/"
        labels.append(f"--- Your Pages URL will be: {pages_url} ---")
        labels.append("Save & Exit")
        c = d.select("Wizard Settings", labels)
        if c < 0 or c == len(labels)-1:
            v['wizard_settings'] = ws; save_vault(v); return
        if c == len(labels)-2: continue
        k, lbl = fields[c]
        ws[k] = d.input(lbl, ws.get(k, ''))

def _ws():
    return load_vault().get('wizard_settings', {})

def _require_ws():
    ws = _ws()
    if not ws.get('gh_user') or not ws.get('gh_repo'):
        xbmcgui.Dialog().ok("Setup needed", "Open 'Wizard Settings' first and enter your GitHub username and repo name.")
        return None
    return ws

def _pick_zip(exports):
    zips = sorted([f for f in os.listdir(exports) if f.endswith('.zip')])
    if not zips:
        xbmcgui.Dialog().ok("No builds", "Create a build first with SAVE MY BUILD.")
        return None
    i = xbmcgui.Dialog().select("Select build", zips)
    return os.path.join(exports, zips[i]) if i >= 0 else None

def _md5(path):
    import hashlib
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''): h.update(chunk)
    return h.hexdigest()

def bwc_gen_xml(exports):
    ws = _require_ws()
    if not ws: return
    zpath = _pick_zip(exports)
    if not zpath: return
    d = xbmcgui.Dialog()
    name = d.input("Build display name", os.path.basename(zpath)[:-4])
    if not name: return
    ver = d.input("Version", "1.0.0")
    kodi_min = ["19", "20", "21"][max(0, d.select("Minimum Kodi version", ["19 Matrix", "20 Nexus", "21 Omega"]))]
    changelog = d.input("Changelog (one line or \\n for new lines)", "Initial release")
    pages = f"https://{ws['gh_user']}.github.io/{ws['gh_repo']}/"
    url = d.input("Public zip URL", pages + "builds/" + os.path.basename(zpath))
    size = os.path.getsize(zpath)
    md5 = _md5(zpath)
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<wizard>
  <build>
    <name>{name}</name>
    <version>{ver}</version>
    <kodi>{kodi_min}</kodi>
    <author>{ws.get('author','')}</author>
    <url>{url}</url>
    <md5>{md5}</md5>
    <size>{size}</size>
    <icon>{ws.get('icon_url','')}</icon>
    <fanart>{ws.get('fanart_url','')}</fanart>
    <support>{ws.get('support_url','')}</support>
    <created>{time.strftime('%Y-%m-%d %H:%M:%S')}</created>
    <changelog>{changelog}</changelog>
  </build>
</wizard>
'''
    out = os.path.join(exports, 'wizard.xml')
    with open(out, 'w', encoding='utf-8') as f: f.write(xml)
    d.ok("wizard.xml created", f"Saved to:\n{out}\n\nMD5: {md5}\nSize: {size/1048576:.1f} MB")

def bwc_scaffold(exports):
    ws = _require_ws()
    if not ws: return
    zpath = _pick_zip(exports)
    if not zpath: return
    # Ensure wizard.xml exists
    xml_path = os.path.join(exports, 'wizard.xml')
    if not os.path.exists(xml_path):
        if xbmcgui.Dialog().yesno("Missing wizard.xml", "No wizard.xml yet. Generate it now?"):
            bwc_gen_xml(exports)
        if not os.path.exists(xml_path): return
    repo_dir = os.path.join(exports, ws['gh_repo'])
    os.makedirs(os.path.join(repo_dir, 'builds'), exist_ok=True)
    shutil.copy2(zpath, os.path.join(repo_dir, 'builds', os.path.basename(zpath)))
    shutil.copy2(xml_path, os.path.join(repo_dir, 'wizard.xml'))
    pages = f"https://{ws['gh_user']}.github.io/{ws['gh_repo']}/"
    readme = f"""# {ws.get('author','My')} Kodi Builds

## Install the wizard on Kodi
1. In Kodi: Settings > System > Add-ons > enable **Unknown sources**
2. Settings > File manager > Add source: `{pages}`  (name it anything)
3. Install from zip file > pick that source > install the wizard zip
4. Open the wizard addon > pick your build > done

## Files
- `wizard.xml` - build manifest (auto-generated)
- `builds/` - your build zip(s)
"""
    instructions = f"""HOW TO PUBLISH (no command line needed)

1. Go to https://github.com and sign up (free).
2. Click 'New repository'. Name it EXACTLY: {ws['gh_repo']}
   - Set to PUBLIC. Tick 'Add README'. Create.
3. In the new repo click 'Add file' > 'Upload files'.
4. Drag the ENTIRE contents of this folder in:
   {repo_dir}
5. Commit changes.
6. Repo > Settings > Pages > Source = 'Deploy from branch' > main / root > Save.
7. Wait ~1 minute. Your site is live at:
   {pages}

Direct URLs users will use:
- wizard.xml : {pages}wizard.xml
- build zip  : {pages}builds/{os.path.basename(zpath)}
"""
    with open(os.path.join(repo_dir, 'README.md'), 'w') as f: f.write(readme)
    with open(os.path.join(repo_dir, 'INSTRUCTIONS.txt'), 'w') as f: f.write(instructions)
    xbmcgui.Dialog().ok("Repo scaffold ready", f"Folder:\n{repo_dir}\n\nOpen it with a file manager and follow INSTRUCTIONS.txt")

def bwc_gen_wizard_addon(exports):
    import zipfile
    ws = _require_ws()
    if not ws: return
    addon_id = ws.get('addon_id') or f"program.{ws['gh_user']}.wizard"
    pages = f"https://{ws['gh_user']}.github.io/{ws['gh_repo']}/"
    wizard_xml_url = pages + "wizard.xml"
    addon_name = xbmcgui.Dialog().input("Wizard addon name", f"{ws.get('author','My')} Build Wizard")
    if not addon_name: return
    version = "1.0.0"
    # addon.xml
    addon_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<addon id="{addon_id}" name="{addon_name}" version="{version}" provider-name="{ws.get('author','')}">
    <requires><import addon="xbmc.python" version="3.0.0"/></requires>
    <extension point="xbmc.python.pluginsource" library="main.py"><provides>executable</provides></extension>
    <extension point="xbmc.addon.metadata">
        <summary lang="en">{addon_name}</summary>
        <description lang="en">Install builds from {ws.get('author','')}.</description>
        <platform>all</platform>
        <assets><icon>icon.png</icon></assets>
    </extension>
</addon>
'''
    main_py = f'''import xbmc, xbmcgui, xbmcvfs, sys, os, urllib.request, ssl, hashlib, zipfile, xml.etree.ElementTree as ET
WIZARD_XML = "{wizard_xml_url}"
def _get(url):
    ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    req = urllib.request.Request(url, headers={{'User-Agent':'KodiWizard/1.0'}})
    return urllib.request.urlopen(req, context=ctx, timeout=30).read()
def main():
    d = xbmcgui.Dialog()
    try:
        root = ET.fromstring(_get(WIZARD_XML))
    except Exception as e:
        d.ok("Wizard", f"Cannot load manifest:\\n{{e}}"); return
    builds = root.findall('build')
    if not builds: d.ok("Wizard","No builds listed."); return
    labels = [f"{{b.find('name').text}} v{{b.find('version').text}}" for b in builds]
    i = d.select("Pick a build", labels)
    if i < 0: return
    b = builds[i]
    url = b.find('url').text; md5 = (b.find('md5').text or '').strip()
    if not d.yesno("Install", f"Install {{labels[i]}}?\\nThis will overwrite current setup."): return
    p = xbmcgui.DialogProgress(); p.create("Downloading build","Please wait...")
    tmp = xbmcvfs.translatePath('special://temp/wizard_build.zip')
    try:
        data = _get(url)
        with open(tmp,'wb') as f: f.write(data)
        if md5 and hashlib.md5(open(tmp,'rb').read()).hexdigest() != md5:
            p.close(); d.ok("Wizard","MD5 mismatch. Aborting."); return
        p.update(60,"Extracting...")
        home = xbmcvfs.translatePath('special://home/')
        with zipfile.ZipFile(tmp) as zf: zf.extractall(home)
        p.close(); d.ok("Done","Build installed. Restart Kodi.")
    except Exception as e:
        p.close(); d.ok("Failed", str(e))
main()
'''
    # Build a tiny themed icon (solid dark + cyan square)
    icon_bytes = open(os.path.join(MEDIA_PATH, 'build.png'), 'rb').read()
    out_zip = os.path.join(exports, f"{addon_id}-{version}.zip")
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{addon_id}/addon.xml", addon_xml)
        zf.writestr(f"{addon_id}/main.py", main_py)
        zf.writestr(f"{addon_id}/icon.png", icon_bytes)
    xbmcgui.Dialog().ok("Wizard addon created", f"Saved to:\n{out_zip}\n\nUpload it into your repo at builds/ or tell users to install it directly.")

def bwc_instructions():
    ws = _ws()
    pages = f"https://{ws.get('gh_user','<user>')}.github.io/{ws.get('gh_repo','<repo>')}/"
    text = (
        "[COLOR cyan]PUBLISH YOUR BUILD ON GITHUB (free, no command line)[/COLOR]\n\n"
        "[COLOR yellow]1. GitHub account[/COLOR]\n- Go to github.com > Sign up (free).\n\n"
        "[COLOR yellow]2. Create repo[/COLOR]\n- Click + > New repository.\n"
        f"- Name it: {ws.get('gh_repo','<repo>')} (must match your Wizard Settings).\n- Public. Tick 'Add README'. Create.\n\n"
        "[COLOR yellow]3. Generate scaffold[/COLOR]\n- In this menu pick 'Generate Repo Scaffold'.\n- It creates a folder on your device with wizard.xml + your build.zip + README + INSTRUCTIONS.\n\n"
        "[COLOR yellow]4. Upload[/COLOR]\n- Open the repo in your browser.\n- 'Add file' > 'Upload files' > drag the scaffold contents in > Commit.\n\n"
        "[COLOR yellow]5. Enable Pages[/COLOR]\n- Repo Settings > Pages > Source = main / root > Save.\n- Wait ~1 minute.\n\n"
        f"[COLOR yellow]6. Your public URLs[/COLOR]\n- Site:       {pages}\n- Manifest:   {pages}wizard.xml\n\n"
        "[COLOR yellow]7. Wizard addon[/COLOR]\n- Pick 'Generate Companion Wizard Addon'.\n- Share that .zip with users - they install it once and get your builds forever.\n\n"
        "[COLOR yellow]8. Updating a build[/COLOR]\n- Make a new build > regenerate wizard.xml > re-upload wizard.xml + new zip. Done.\n"
    )
    xbmcgui.Dialog().textviewer("How To Publish", text)

# ============================================
# ROUTER
# ============================================
if __name__ == '__main__':
    # Check auto-clean on startup
    check_auto_clean_on_startup()
    
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
    action = params.get('action')
    
    if not action:
        main_menu()
    elif action == 'speed':
        speed_optimizer()
    elif action == 'speedtest':
        speed_test_menu()
    elif action == 'autoclean':
        auto_clean_settings()
    elif action == 'auth':
        auth_menu()
    elif action == 'auth_rd':
        auth_real_debrid()
    elif action == 'auth_pm':
        auth_premiumize()
    elif action == 'auth_ad':
        auth_alldebrid()
    elif action == 'auth_trakt':
        auth_trakt()
    elif action == 'auth_tb':
        auth_torbox()
    elif action == 'auth_tmdb':
        auth_tmdb()
    elif action == 'sync_all':
        sync_all_addons()
    elif action == 'account_cards':
        show_account_cards()
    elif action == 'iptv':
        iptv_vault()
    elif action == 'favs':
        favourites_vault()
    elif action == 'usb':
        usb_manager()
    elif action == 'restore':
        one_click_restore()
    elif action == 'repair':
        repair_addons()
    elif action == 'clean':
        clear_cache_menu()
    elif action == 'packages':
        clear_packages()
    elif action == 'help':
        help_menu()
    elif action == 'buy_beer':
        import ssl
        kofi_url = 'https://ko-fi.com/zeus768'
        qr_file = os.path.join(KODI_TEMP, 'kofi_qr.png')
        try:
            ctx = ssl._create_unverified_context()
            req = urllib.request.Request(
                f'https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(kofi_url)}&bgcolor=0-0-0&color=255-255-255',
                headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                with open(qr_file, 'wb') as f:
                    f.write(resp.read())
            xbmc.executebuiltin(f'ShowPicture({qr_file})')
            xbmc.sleep(300)
        except:
            pass
        xbmcgui.Dialog().ok('Support zeus768', 'Scan QR or visit:\n[COLOR cyan]https://ko-fi.com/zeus768[/COLOR]')
        try:
            xbmc.executebuiltin('Action(Back)')
        except:
            pass
    elif action == 'refresh_widgets':
        refresh_widgets()
    elif action == 'log_uploader':
        log_uploader_menu()
    elif action == 'account_cards':
        show_account_cards()
    elif action == 'wizard_creator':
        build_wizard_menu()
    elif action == 'main':
        main_menu()
    elif action == 'save_build':
        save_my_build()

