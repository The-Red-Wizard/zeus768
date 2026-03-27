import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs
import json, os, sys, shutil, urllib.parse, time

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
              f"Freed approximately {saved:.1f} MB",
              "System optimized! Restart Kodi for best results.")

# ============================================
# AUTHENTICATION MANAGER
# ============================================
def auth_menu():
    """Authentication sub-menu"""
    items = [
        ("Real-Debrid Authorization", "auth_rd", "rd.png"),
        ("Premiumize Authorization", "auth_pm", "pm.png"),
        ("AllDebrid Authorization", "auth_ad", "ad.png"),
        ("Trakt Authorization", "auth_trakt", "trakt.png"),
        ("TMDB API Key Setup", "auth_tmdb", "tmdb.png"),
        ("Sync All to Addons", "sync_all", "sync.png"),
        ("Back to Main Menu", "main", "restore.png")
    ]
    for label, act, icon in items:
        li = xbmcgui.ListItem(label=label)
        art = get_art(icon)
        li.setArt({'icon': art, 'thumb': art, 'fanart': ADDON_FANART})
        url = f"{sys.argv[0]}?action={act}"
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True if act in ['main'] else False)
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
    """Real-Debrid authorization"""
    dialog = xbmcgui.Dialog()
    vault = load_vault()
    
    current_token = vault.get('rd_token', 'Not Set')
    display_token = current_token[:20] + '...' if len(current_token) > 20 else current_token
    
    choice = dialog.select("Real-Debrid", [
        f"Current: {display_token}",
        "Enter API Token Manually",
        "Clear Real-Debrid Token",
        "Help: How to get RD Token"
    ])
    
    if choice == 1:
        token = dialog.input("Enter Real-Debrid API Token")
        if token:
            vault['rd_token'] = token
            if save_vault(vault):
                notify("Real-Debrid", "Token Saved Successfully!")
            else:
                dialog.ok("Error", "Failed to save token")
    elif choice == 2:
        vault.pop('rd_token', None)
        save_vault(vault)
        notify("Real-Debrid", "Token Cleared")
    elif choice == 3:
        dialog.ok("Real-Debrid Help",
                  "1. Go to real-debrid.com",
                  "2. Login and go to API page",
                  "3. Copy your API token")

def auth_premiumize():
    """Premiumize authorization"""
    dialog = xbmcgui.Dialog()
    vault = load_vault()
    
    current_token = vault.get('pm_token', 'Not Set')
    display_token = current_token[:20] + '...' if len(current_token) > 20 else current_token
    
    choice = dialog.select("Premiumize", [
        f"Current: {display_token}",
        "Enter API Key Manually",
        "Clear Premiumize Key",
        "Help: How to get PM Key"
    ])
    
    if choice == 1:
        token = dialog.input("Enter Premiumize API Key")
        if token:
            vault['pm_token'] = token
            if save_vault(vault):
                notify("Premiumize", "Key Saved Successfully!")
    elif choice == 2:
        vault.pop('pm_token', None)
        save_vault(vault)
        notify("Premiumize", "Key Cleared")
    elif choice == 3:
        dialog.ok("Premiumize Help",
                  "1. Go to premiumize.me",
                  "2. Login and go to Account",
                  "3. Copy your API Key")

def auth_alldebrid():
    """AllDebrid authorization"""
    dialog = xbmcgui.Dialog()
    vault = load_vault()
    
    current_token = vault.get('ad_token', 'Not Set')
    display_token = current_token[:20] + '...' if len(current_token) > 20 else current_token
    
    choice = dialog.select("AllDebrid", [
        f"Current: {display_token}",
        "Enter API Key Manually",
        "Clear AllDebrid Key",
        "Help: How to get AD Key"
    ])
    
    if choice == 1:
        token = dialog.input("Enter AllDebrid API Key")
        if token:
            vault['ad_token'] = token
            if save_vault(vault):
                notify("AllDebrid", "Key Saved Successfully!")
    elif choice == 2:
        vault.pop('ad_token', None)
        save_vault(vault)
        notify("AllDebrid", "Key Cleared")
    elif choice == 3:
        dialog.ok("AllDebrid Help",
                  "1. Go to alldebrid.com",
                  "2. Login and go to API Keys",
                  "3. Generate and copy your key")

def auth_trakt():
    """Trakt authorization"""
    dialog = xbmcgui.Dialog()
    vault = load_vault()
    
    current_token = vault.get('trakt_token', 'Not Set')
    display_token = current_token[:20] + '...' if len(current_token) > 20 else current_token
    
    choice = dialog.select("Trakt", [
        f"Current: {display_token}",
        "Enter Client ID",
        "Enter Client Secret", 
        "Clear Trakt Auth",
        "Help: How to setup Trakt"
    ])
    
    if choice == 1:
        token = dialog.input("Enter Trakt Client ID")
        if token:
            vault['trakt_client_id'] = token
            if save_vault(vault):
                notify("Trakt", "Client ID Saved!")
    elif choice == 2:
        token = dialog.input("Enter Trakt Client Secret")
        if token:
            vault['trakt_client_secret'] = token
            vault['trakt_token'] = 'Configured'
            if save_vault(vault):
                notify("Trakt", "Client Secret Saved!")
    elif choice == 3:
        vault.pop('trakt_client_id', None)
        vault.pop('trakt_client_secret', None)
        vault.pop('trakt_token', None)
        save_vault(vault)
        notify("Trakt", "Auth Cleared")
    elif choice == 4:
        dialog.ok("Trakt Help",
                  "1. Go to trakt.tv/oauth/applications",
                  "2. Create a new application",
                  "3. Copy Client ID and Secret")

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
                  "1. Go to themoviedb.org",
                  "2. Create account, go to Settings > API",
                  "3. Request API key and copy v3 auth")

def sync_tmdb_helper():
    """Sync TMDB to TMDBHelper addon"""
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
    """Sync all credentials to supported addons"""
    vault = load_vault()
    dialog = xbmcgui.Dialog()
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("The Accountant", "Syncing credentials...")
    
    synced = []
    failed = []
    
    # Common video addons to sync
    addon_mappings = {
        'plugin.video.fen': {
            'rd': ('rd.token', 'rd_token'),
            'pm': ('pm.token', 'pm_token'),
            'ad': ('ad.token', 'ad_token'),
            'trakt': ('trakt.client_id', 'trakt_client_id')
        },
        'plugin.video.ezra': {
            'rd': ('rd.token', 'rd_token'),
            'pm': ('pm.token', 'pm_token'),
            'ad': ('ad.token', 'ad_token')
        },
        'plugin.video.coalition': {
            'rd': ('realdebrid.token', 'rd_token'),
            'pm': ('premiumize.token', 'pm_token')
        },
        'plugin.video.themoviedb.helper': {
            'tmdb': ('tmdb_api_key', 'tmdb_api_key')
        },
        'plugin.video.seren': {
            'rd': ('rd.auth', 'rd_token'),
            'pm': ('premiumize.token', 'pm_token'),
            'ad': ('alldebrid.apikey', 'ad_token')
        },
        'plugin.video.umbrella': {
            'rd': ('realdebrid.token', 'rd_token'),
            'pm': ('premiumize.token', 'pm_token'),
            'ad': ('alldebrid.token', 'ad_token')
        }
    }
    
    total = len(addon_mappings)
    current = 0
    
    for addon_id, settings_map in addon_mappings.items():
        current += 1
        pDialog.update(int((current/total)*100), f"Checking {addon_id}...")
        
        try:
            target_addon = xbmcaddon.Addon(addon_id)
            for service, (setting_name, vault_key) in settings_map.items():
                value = vault.get(vault_key, '')
                if value:
                    target_addon.setSetting(setting_name, value)
            synced.append(addon_id.split('.')[-1])
        except:
            failed.append(addon_id.split('.')[-1])
    
    pDialog.close()
    
    msg = ""
    if synced:
        msg += f"Synced: {', '.join(synced)}\n"
    if failed:
        msg += f"Not installed: {', '.join(failed)}"
    
    dialog.ok("Sync Complete", msg if msg else "No addons to sync")

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
            url = dialog.input("M3U URL or Server URL")
            username = dialog.input("Username (optional)")
            password = dialog.input("Password (optional)")
            
            iptv_data[name] = {
                'url': url,
                'username': username,
                'password': password
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
    """Export IPTV settings to PVR IPTV Simple Client"""
    dialog = xbmcgui.Dialog()
    providers = list(iptv_data.keys())
    
    choice = dialog.select("Select Provider to Export", providers)
    if choice >= 0:
        provider = providers[choice]
        data = iptv_data[provider]
        
        try:
            pvr = xbmcaddon.Addon('pvr.iptvsimple')
            pvr.setSetting('m3uPathType', '1')  # Remote URL
            pvr.setSetting('m3uUrl', data.get('url', ''))
            notify("IPTV Export", f"{provider} exported to PVR IPTV Simple")
        except:
            dialog.ok("Export Failed", "PVR IPTV Simple Client not installed")

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
                  f"Current Favourites: {current_exists}",
                  f"Backup Exists: {backup_exists}",
                  f"Backup Date: {backup_date}")
                  
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
        dialog.ok("Restore Complete", f"Restored: {', '.join(restored)}", "Restart Kodi for full effect")
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
    dialog.ok("Dependencies", "Dependency check complete", "Restart Kodi if issues persist")

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
            if dialog.yesno("Warning", f"This will delete ALL data for {addon_id}", "Continue?"):
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
                  f"Total Packages: {pkg_count}",
                  f"Total Size: {pkg_size:.1f} MB",
                  f"Location: {KODI_PACKAGES}")
                  
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
                  "Version: 3.9.4",
                  "Author: zeus768",
                  "Master Pro Suite for Kodi maintenance")
                  
    elif choice == 1:
        dialog.ok("Speed Optimizer",
                  "Clears temp files, old thumbnails, and packages.",
                  "Run weekly for best performance.",
                  "Restart Kodi after optimization.")
                  
    elif choice == 2:
        dialog.ok("Authentication Setup",
                  "1. Enter your API keys/tokens in Auth menu",
                  "2. Use 'Sync All' to push to addons",
                  "3. Credentials are stored securely in vault")
                  
    elif choice == 3:
        dialog.ok("Backup & Restore",
                  "USB Backup: Export/import vault to USB drive",
                  "Favourites Vault: Backup your Kodi favourites",
                  "One-Click Restore: Restore all saved data")
                  
    elif choice == 4:
        dialog.ok("Troubleshooting",
                  "Addons not working? Try 'Repair Video Addons'",
                  "Slow performance? Run 'Speed Optimizer'",
                  "Lost settings? Use 'One-Click Restore'")
                  
    elif choice == 5:
        dialog.ok("Credits",
                  "The Accountant by zeus768",
                  "Master Pro Suite v3.9.4",
                  "Thank you for using this addon!")

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
# MAIN MENU
# ============================================
def main_menu():
    """Main menu display"""
    items = [
        ("ONE-CLICK SPEED OPTIMIZER", "speed", "speed.png"),
        ("SCHEDULED AUTO-CLEAN", "autoclean", "autoclean.png"),
        ("Pair RD / Trakt / Auth / PM / AD / TMDB", "auth", "auth.png"),
        ("IPTV Login Vault", "iptv", "iptv.png"),
        ("Favourites Vault", "favs", "favs.png"),
        ("USB BACKUP TOOL", "usb", "usb.png"),
        ("ONE-CLICK RESTORE (ALL)", "restore", "restore.png"),
        ("SYNC ALL TO ADDONS", "sync_all", "sync.png"),
        ("--- Maintenance Tools ---", "spacer", ""),
        ("REPAIR VIDEO ADDONS", "repair", "repair.png"),
        ("CLEAR CACHE (MANUAL)", "clean", "clean.png"),
        ("CLEAR PACKAGES", "packages", "packages.png"),
        ("--- Help & Info ---", "spacer", ""),
        ("HELP / GUIDE", "help", "help.png")
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
    elif action == 'auth_tmdb':
        auth_tmdb()
    elif action == 'sync_all':
        sync_all_addons()
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
    elif action == 'main':
        main_menu()
