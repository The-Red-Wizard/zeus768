"""
The Accountant - Authorisation Matrix

Shows, per installed addon, which services are authorised and with which
account. The check is empirical: we read each addon's on-disk settings
(via xbmcaddon.getSetting) and compare against the vault, then query the
upstream APIs to resolve each stored token to a human-readable account.
"""
import xbmc
import xbmcaddon

# Which setting id(s) to check for each service, plus the vault key used
# for "is this synced from Accountant?" comparison.
SERVICE_SETTING_KEYS = {
    'RD': {
        'vault_key': 'rd_token',
        'patterns': ['rd_access_token', 'rd_token', 'realdebrid_token', 'rd.auth',
                     'rd.token', 'realdebrid.token'],
    },
    'PM': {
        'vault_key': 'pm_token',
        'patterns': ['pm_access_token', 'pm_token', 'pm.token',
                     'premiumize.token', 'premiumize.apikey', 'premiumize_token'],
    },
    'AD': {
        'vault_key': 'ad_token',
        'patterns': ['ad_api_key', 'ad_token', 'ad.token',
                     'alldebrid.token', 'alldebrid.apikey', 'alldebrid_token'],
    },
    'TB': {
        'vault_key': 'tb_token',
        'patterns': ['tb_api_key', 'tb_token', 'tb.token', 'torbox.apikey', 'torbox_token'],
    },
    'Trakt': {
        'vault_key': 'trakt_token',
        'patterns': ['trakt_access_token', 'trakt_token', 'trakt.auth',
                     'trakt.token', 'trakt_oauth_token'],
    },
}


def _mask(value):
    if not value:
        return ''
    value = str(value)
    if len(value) <= 8:
        return '*' * len(value)
    return value[:4] + '...' + value[-4:]


def _read_settings(addon_id, patterns):
    """Try each pattern and return the first non-empty value from the addon's
    settings. Returns (setting_id, value) or (None, '')."""
    try:
        addon = xbmcaddon.Addon(addon_id)
    except Exception:
        return None, ''
    for p in patterns:
        try:
            v = addon.getSetting(p)
        except Exception:
            v = ''
        if v:
            return p, v
    return None, ''


def scan_addon_auth(addon_ids):
    """Build the auth matrix for the given addon ids.

    Returns list of dicts:
      { 'addon_id', 'installed', 'services': { 'RD': {'status', 'value', 'setting_id', 'synced'}}, ... }
    """
    from resources.lib import auth_manager

    vault = {}
    try:
        # Main.py holds the canonical loader, but we can replicate the file read
        import json, os, xbmcvfs
        deep = xbmcvfs.translatePath('special://userdata/the_accountant_vault.json')
        if os.path.isfile(deep):
            with open(deep, 'r') as f:
                vault = json.load(f)
    except Exception:
        pass

    results = []
    for aid in addon_ids:
        entry = {'addon_id': aid, 'installed': False, 'services': {}}
        try:
            xbmcaddon.Addon(aid)
            entry['installed'] = True
        except Exception:
            results.append(entry)
            continue

        for service, meta in SERVICE_SETTING_KEYS.items():
            sid, value = _read_settings(aid, meta['patterns'])
            vault_value = vault.get(meta['vault_key'], '')
            synced = bool(value and vault_value and value == vault_value)
            entry['services'][service] = {
                'status': 'set' if value else 'unset',
                'setting_id': sid,
                'value_masked': _mask(value),
                'synced': synced,
                'raw': value,
            }
        results.append(entry)
    return results


def resolve_accounts(vault):
    """Use the stored tokens to look up account usernames.

    Returns dict: { 'RD': 'user_abc', 'PM': '12345', 'AD': 'user', 'Trakt': 'handle' }
    """
    from resources.lib import auth_manager
    accounts = {}
    if vault.get('rd_token'):
        info = auth_manager.get_rd_account_info(vault['rd_token'])
        if info:
            accounts['RD'] = f"{info['username']} ({info['status']}, {info['days_left']}d)"
    if vault.get('pm_token'):
        info = auth_manager.get_pm_account_info(vault['pm_token'])
        if info:
            accounts['PM'] = f"{info['customer_id']} ({info['status']}, {info['days_left']}d)"
    if vault.get('ad_token'):
        info = auth_manager.get_ad_account_info(vault['ad_token'])
        if info:
            accounts['AD'] = f"{info['username']} ({info['status']}, {info['days_left']}d)"
    if vault.get('trakt_token'):
        info = auth_manager.get_trakt_account_info(vault['trakt_token'])
        if info:
            accounts['Trakt'] = f"{info['username']} ({info['vip']})"
    return accounts


def render_matrix(entries, accounts, iptv_providers=None):
    """Return a human-readable multi-line string summarising the auth matrix."""
    lines = []
    lines.append('=' * 58)
    lines.append('VAULT ACCOUNTS (source of truth)')
    lines.append('=' * 58)
    for svc in ('RD', 'PM', 'AD', 'Trakt'):
        val = accounts.get(svc)
        lines.append(f"  {svc:<6s} {val if val else '[not authorised]'}")
    if iptv_providers:
        lines.append(f"  IPTV   {len(iptv_providers)} provider(s): {', '.join(iptv_providers[:5])}")
    lines.append('')
    lines.append('=' * 58)
    lines.append('AUTHORISED ADDONS')
    lines.append('=' * 58)

    # Sort: addons with any auth first
    def _any_set(e):
        return any(s['status'] == 'set' for s in e['services'].values())
    entries_sorted = sorted(
        [e for e in entries if e['installed']],
        key=lambda e: (not _any_set(e), e['addon_id'])
    )

    for e in entries_sorted:
        if not _any_set(e):
            continue
        lines.append('')
        lines.append(e['addon_id'])
        for svc, info in e['services'].items():
            if info['status'] == 'set':
                tag = '[SYNCED]' if info['synced'] else '[external]'
                lines.append(f"   {svc:<6s} {tag}  {info['value_masked']}  ({info['setting_id']})")
            # don't print empty services in the summary

    # Summary stats
    total = sum(1 for e in entries if e['installed'])
    authed = sum(1 for e in entries if e['installed'] and _any_set(e))
    lines.append('')
    lines.append('=' * 58)
    lines.append(f'SUMMARY: {authed} of {total} installed addon(s) authorised')
    lines.append('=' * 58)
    return '\n'.join(lines)


def render_detail(entry, accounts):
    """Detailed per-addon view for the drill-down dialog."""
    aid = entry['addon_id']
    lines = [aid, '=' * len(aid), '']
    if not entry['installed']:
        lines.append('Addon is not installed on this device.')
        return '\n'.join(lines)
    any_set = False
    for svc, info in entry['services'].items():
        if info['status'] == 'set':
            any_set = True
            tag = 'SYNCED from Accountant' if info['synced'] else 'SET (external - does not match vault)'
            acc = accounts.get(svc, '')
            lines.append(f"{svc}")
            lines.append(f"  Status:     {tag}")
            lines.append(f"  Setting ID: {info['setting_id']}")
            lines.append(f"  Value:      {info['value_masked']}")
            if acc:
                lines.append(f"  Account:    {acc}")
            lines.append('')
        else:
            lines.append(f"{svc}")
            lines.append(f"  Status:     not authorised")
            lines.append('')
    if not any_set:
        lines.append('No services authorised for this addon.')
    return '\n'.join(lines)
