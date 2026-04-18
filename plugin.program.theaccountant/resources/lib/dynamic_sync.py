"""
The Accountant - Dynamic Addon Auth Scanner
Auto-detects installed Kodi addons and pushes vault credentials into any
settings.xml that contains recognised RD/PM/AD/TB/Trakt/TMDB setting keys.

This makes the sync future-proof: no hardcoded addon IDs required.
"""
import os
import re
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui

# Regex pattern that matches any <setting id="..."> or id='...' entry in a settings.xml
SETTING_ID_RE = re.compile(r'''<setting\b[^>]*\bid\s*=\s*["']([^"']+)["']''', re.IGNORECASE)

# Map of vault keys -> list of regex patterns that match target addon setting IDs.
# Patterns are matched case-insensitively against the full setting id.
# Order matters: first match wins for each vault key (most specific first).
PATTERN_MAP = {
    # ---- Real-Debrid ----
    'rd_token': [
        r'^rd[._-]?(access[._-]?)?(token|auth)$',
        r'^realdebrid[._-]?(access[._-]?)?(token|auth)$',
        r'^real[._-]?debrid[._-]?(access[._-]?)?(token|auth)$',
        r'^RealDebridResolver[._-]?token$',
    ],
    'rd_refresh': [
        r'^rd[._-]?refresh([._-]?token)?$',
        r'^realdebrid[._-]?refresh([._-]?token)?$',
        r'^RealDebridResolver[._-]?refresh$',
    ],
    'rd_client_id': [
        r'^rd[._-]?client[._-]?id$',
        r'^realdebrid[._-]?client[._-]?id$',
        r'^RealDebridResolver[._-]?client[._-]?id$',
    ],
    'rd_client_secret': [
        r'^rd[._-]?(client[._-]?)?secret$',
        r'^realdebrid[._-]?(client[._-]?)?secret$',
        r'^RealDebridResolver[._-]?(client[._-]?)?secret$',
    ],
    'rd_expires': [
        r'^rd[._-]?(expires?|expiry|expires_at|expiration)$',
        r'^realdebrid[._-]?(expires?|expiry|expires_at|expiration)$',
    ],
    # ---- Premiumize ----
    'pm_token': [
        r'^pm[._-]?(access[._-]?)?(token|apikey|api[._-]?key)$',
        r'^premiumize[._-]?(access[._-]?)?(token|apikey|api[._-]?key)$',
        r'^PremiumizeMeResolver[._-]?(token|apikey)$',
    ],
    # ---- AllDebrid ----
    'ad_token': [
        r'^ad[._-]?(access[._-]?)?(token|apikey|api[._-]?key)$',
        r'^alldebrid[._-]?(access[._-]?)?(token|apikey|api[._-]?key)$',
        r'^all[._-]?debrid[._-]?(token|apikey|api[._-]?key)$',
        r'^AlldebridResolver[._-]?(token|apikey)$',
    ],
    # ---- TorBox ----
    'tb_token': [
        r'^tb[._-]?(access[._-]?)?(token|apikey|api[._-]?key)$',
        r'^torbox[._-]?(access[._-]?)?(token|apikey|api[._-]?key)$',
        r'^tor[._-]?box[._-]?(token|apikey|api[._-]?key)$',
    ],
    # ---- Trakt ----
    'trakt_token': [
        r'^trakt[._-]?(access[._-]?)?(token|auth)$',
    ],
    'trakt_refresh': [
        r'^trakt[._-]?refresh([._-]?token)?$',
    ],
    'trakt_expires': [
        r'^trakt[._-]?(expires?|expiry|expires_at|expiration)$',
    ],
    # ---- TMDB ----
    'tmdb_api_key': [
        r'^tmdb[._-]?(api[._-]?key|apikey)$',
        r'^(themoviedb|moviedb)[._-]?(api[._-]?key|apikey)$',
    ],
}

# Compile all patterns once
_COMPILED = {
    vault_key: [re.compile(p, re.IGNORECASE) for p in patterns]
    for vault_key, patterns in PATTERN_MAP.items()
}

# Addon IDs we must NEVER touch (our own addon, core Kodi, debrid reserved ids)
_SKIP_PREFIXES = (
    'plugin.program.theaccountant',
    'metadata.',
    'skin.',
    'weather.',
    'service.xbmc.',
    'xbmc.',
    'kodi.',
    'os.',
)


def _find_settings_files(addon_path):
    """Return list of candidate settings.xml files inside addon/resources.

    Kodi addons may store settings in:
      - resources/settings.xml (legacy)
      - resources/settings/*.xml (newer split layout)
    """
    files = []
    res = os.path.join(addon_path, 'resources')
    legacy = os.path.join(res, 'settings.xml')
    if os.path.isfile(legacy):
        files.append(legacy)
    split_dir = os.path.join(res, 'settings')
    if os.path.isdir(split_dir):
        try:
            for f in os.listdir(split_dir):
                if f.lower().endswith('.xml'):
                    files.append(os.path.join(split_dir, f))
        except Exception:
            pass
    return files


def _extract_setting_ids(xml_path):
    """Parse a settings.xml and return the set of setting id attributes found."""
    ids = set()
    try:
        with open(xml_path, 'r', encoding='utf-8', errors='ignore') as fh:
            content = fh.read()
        for m in SETTING_ID_RE.finditer(content):
            ids.add(m.group(1))
    except Exception as e:
        xbmc.log(f'[Accountant] Failed to parse {xml_path}: {e}', xbmc.LOGDEBUG)
    return ids


def _map_ids_to_vault(setting_ids):
    """For each setting id, determine which vault key (if any) it corresponds to.
    Returns dict: { setting_id: vault_key }
    """
    mapping = {}
    for sid in setting_ids:
        for vault_key, regexes in _COMPILED.items():
            if any(rx.match(sid) for rx in regexes):
                mapping[sid] = vault_key
                break
    return mapping


def scan_installed_addons(addons_root=None):
    """Walk the Kodi addons folder and return a list of detected targets.

    Each entry is a dict:
      {
        'addon_id': 'plugin.video.foo',
        'path': '/.../addons/plugin.video.foo',
        'map': { setting_id: vault_key, ... }
      }
    """
    if addons_root is None:
        addons_root = xbmcvfs.translatePath('special://home/addons/')

    results = []
    if not os.path.isdir(addons_root):
        return results

    try:
        addon_dirs = sorted(os.listdir(addons_root))
    except Exception:
        return results

    for addon_id in addon_dirs:
        # Skip obvious non-plugin / non-relevant folders
        if any(addon_id.startswith(p) for p in _SKIP_PREFIXES):
            continue
        if not addon_id.startswith(('plugin.video.', 'plugin.program.',
                                    'script.module.', 'plugin.audio.')):
            continue

        addon_path = os.path.join(addons_root, addon_id)
        if not os.path.isdir(addon_path):
            continue

        ids = set()
        for sfile in _find_settings_files(addon_path):
            ids.update(_extract_setting_ids(sfile))
        if not ids:
            continue

        mapping = _map_ids_to_vault(ids)
        if mapping:
            results.append({
                'addon_id': addon_id,
                'path': addon_path,
                'map': mapping,
            })
    return results


def sync_dynamic(vault, progress_dialog=None, skip_addon_ids=None):
    """Run the dynamic scan and push vault credentials into every detected addon.

    Returns tuple: (synced_addon_ids, details_list)
      details_list items: 'addon_id: key1, key2, ...'
    """
    skip_addon_ids = set(skip_addon_ids or [])
    targets = scan_installed_addons()
    synced = []
    details = []
    total = max(1, len(targets))

    for i, tgt in enumerate(targets):
        addon_id = tgt['addon_id']
        if addon_id in skip_addon_ids:
            continue
        if progress_dialog is not None:
            try:
                progress_dialog.update(int((i / total) * 100), f'Scanning {addon_id}...')
            except Exception:
                pass

        try:
            target = xbmcaddon.Addon(addon_id)
        except Exception:
            continue

        pushed = []
        for setting_id, vault_key in tgt['map'].items():
            value = vault.get(vault_key, '')
            if not value:
                continue
            try:
                target.setSetting(setting_id, str(value))
                pushed.append(setting_id)
            except Exception as e:
                xbmc.log(f'[Accountant] setSetting failed for {addon_id}.{setting_id}: {e}', xbmc.LOGDEBUG)

        if pushed:
            synced.append(addon_id)
            details.append(f"{addon_id}: {', '.join(pushed[:6])}{'...' if len(pushed) > 6 else ''}")

    return synced, details


def preview_scan():
    """Return a human-readable summary of detected addons and matched keys.
    Used by the 'Preview Scan' menu item so the user can see what would sync
    before committing.
    """
    targets = scan_installed_addons()
    lines = [f'Detected {len(targets)} addon(s) with auth settings:', '']
    for tgt in targets:
        lines.append(f"- {tgt['addon_id']}")
        for sid, vkey in sorted(tgt['map'].items()):
            lines.append(f"    {sid}  ->  {vkey}")
        lines.append('')
    return '\n'.join(lines) if targets else 'No installed addons with recognised auth settings were found.'
