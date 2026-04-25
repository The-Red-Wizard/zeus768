# -*- coding: utf-8 -*-
"""ZR Tester - Kodi 21+ video addon.

Browses items from a remote XML feed and resolves playable streams *only*
through ``script.module.zeusresolvers``. Any link the resolver does not
support is shown as non-playable so users can verify exactly what zeus
resolves vs. what it does not.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_ICON = ADDON.getAddonInfo("icon")
ADDON_FANART = ADDON.getAddonInfo("fanart")

HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
PARAMS = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))

XML_URL = "https://pastebin.com/raw/D9MnxHMV"

PROFILE_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
HISTORY_PATH = os.path.join(PROFILE_DIR, "url_history.json")
HISTORY_LIMIT = 25

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[ZR Tester] {msg}", level)


def _build_url(**kwargs):
    return BASE_URL + "?" + urllib.parse.urlencode(kwargs)


def _fetch_xml():
    req = urllib.request.Request(XML_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read().decode("utf-8", errors="replace")
    # Pastebin XML has no root tag; wrap before parsing.
    return f"<root>{data}</root>"


def _parse_items():
    raw = _fetch_xml()
    root = ET.fromstring(raw)
    items = []
    for it in root.findall("item"):
        name = (it.findtext("name") or "").strip()
        content = (it.findtext("content") or "video").strip()
        tmdb = (it.findtext("tmdb") or "").strip()
        link_names = [(e.text or "").strip() for e in it.findall("linkname")]
        link_urls = [(e.text or "").strip() for e in it.findall("link")]
        links = [
            {"name": ln or url, "url": url}
            for ln, url in zip(link_names, link_urls)
        ]
        items.append(
            {
                "name": name,
                "content": content,
                "tmdb": tmdb,
                "links": links,
            }
        )
    return items


def _zeus():
    """Import the Zeus Resolvers module lazily."""
    try:
        import zeusresolvers  # noqa: WPS433

        return zeusresolvers
    except Exception as exc:  # pragma: no cover
        _log(f"zeusresolvers import failed: {exc}", xbmc.LOGERROR)
        return None


def _load_history():
    if not xbmcvfs.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_history(items):
    if not xbmcvfs.exists(PROFILE_DIR):
        xbmcvfs.mkdirs(PROFILE_DIR)
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as fh:
            json.dump(items[:HISTORY_LIMIT], fh)
    except Exception as exc:
        _log(f"history save failed: {exc}", xbmc.LOGWARNING)


def _push_history(url):
    history = [u for u in _load_history() if u != url]
    history.insert(0, url)
    _save_history(history)


def list_root():
    items = _parse_items()
    xbmcplugin.setPluginCategory(HANDLE, "ZR Tester")
    xbmcplugin.setContent(HANDLE, "movies")

    # Top-level "Test custom URL" entry
    tester = xbmcgui.ListItem(
        label="[COLOR cyan][B]\u25B6 Test custom URL\u2026[/B][/COLOR]"
    )
    tester.setArt({"icon": ADDON_ICON, "thumb": ADDON_ICON, "fanart": ADDON_FANART})
    info = tester.getVideoInfoTag()
    info.setTitle("Test custom URL")
    info.setPlot(
        "Paste any hoster URL (Streamtape, DDownload, etc.) and play it through "
        "script.module.zeusresolvers."
    )
    xbmcplugin.addDirectoryItem(
        HANDLE, _build_url(action="prompt"), tester, isFolder=True
    )

    history = _load_history()
    if history:
        h_li = xbmcgui.ListItem(
            label=f"[COLOR yellow]\u23F1 Recent URLs ({len(history)})[/COLOR]"
        )
        h_li.setArt({"icon": ADDON_ICON, "thumb": ADDON_ICON, "fanart": ADDON_FANART})
        xbmcplugin.addDirectoryItem(
            HANDLE, _build_url(action="history"), h_li, isFolder=True
        )

    # Diagnostics entry - quick health check of script.module.zeusresolvers
    diag = xbmcgui.ListItem(
        label="[COLOR lightgreen][B]\u2699 Diagnostics[/B][/COLOR]"
    )
    diag.setArt({"icon": ADDON_ICON, "thumb": ADDON_ICON, "fanart": ADDON_FANART})
    diag_info = diag.getVideoInfoTag()
    diag_info.setTitle("Diagnostics")
    diag_info.setPlot(
        "Run a self-test of script.module.zeusresolvers: shows version, every "
        "supported hoster, and whether its matcher recognises a probe URL. "
        "Optionally probes a live URL end-to-end."
    )
    xbmcplugin.addDirectoryItem(
        HANDLE, _build_url(action="diagnostics"), diag, isFolder=True
    )

    for idx, it in enumerate(items):
        label = it["name"] or f"Item {idx + 1}"
        li = xbmcgui.ListItem(label=label)
        media_type = (
            it["content"]
            if it["content"] in ("movie", "episode", "tvshow")
            else "video"
        )
        li.setArt({"icon": ADDON_ICON, "thumb": ADDON_ICON, "fanart": ADDON_FANART})
        info = li.getVideoInfoTag()
        info.setTitle(label)
        info.setMediaType(media_type)
        if it["tmdb"]:
            info.setUniqueIDs({"tmdb": it["tmdb"]}, "tmdb")
        url = _build_url(action="links", idx=str(idx))
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(HANDLE)


def list_links(idx):
    items = _parse_items()
    it = items[int(idx)]
    xbmcplugin.setPluginCategory(HANDLE, it["name"])
    xbmcplugin.setContent(HANDLE, "videos")

    zeus = _zeus()

    for li_idx, link in enumerate(it["links"]):
        url = link["url"]
        is_http = url.lower().startswith(("http://", "https://"))
        if not is_http:
            label = (
                f"[COLOR red][SKIP][/COLOR] {link['name']}  "
                f"[COLOR grey]({url})[/COLOR]"
            )
            li = xbmcgui.ListItem(label=label)
            li.setArt({"icon": ADDON_ICON})
            xbmcplugin.addDirectoryItem(HANDLE, "", li, isFolder=False)
            continue

        supported = bool(zeus and zeus.can_resolve(url))
        tag = (
            "[COLOR lime][ZR][/COLOR]" if supported else "[COLOR orange][N/A][/COLOR]"
        )
        label = f"{tag} {link['name']}"
        li = xbmcgui.ListItem(label=label)
        li.setArt({"icon": ADDON_ICON, "thumb": ADDON_ICON, "fanart": ADDON_FANART})
        li.setProperty("IsPlayable", "true")
        info = li.getVideoInfoTag()
        info.setTitle(f"{it['name']} - {link['name']}")
        info.setMediaType("video")
        play_url = _build_url(action="play", idx=str(idx), li=str(li_idx))
        xbmcplugin.addDirectoryItem(HANDLE, play_url, li, isFolder=False)

    xbmcplugin.endOfDirectory(HANDLE)


def list_history():
    xbmcplugin.setPluginCategory(HANDLE, "Recent URLs")
    xbmcplugin.setContent(HANDLE, "videos")
    zeus = _zeus()
    for url in _load_history():
        supported = bool(zeus and zeus.can_resolve(url))
        tag = (
            "[COLOR lime][ZR][/COLOR]"
            if supported
            else "[COLOR orange][N/A][/COLOR]"
        )
        host = urllib.parse.urlparse(url).netloc or url
        li = xbmcgui.ListItem(label=f"{tag} {host} - {url}")
        li.setArt({"icon": ADDON_ICON})
        li.setProperty("IsPlayable", "true")
        info = li.getVideoInfoTag()
        info.setTitle(host)
        info.setMediaType("video")
        play_url = _build_url(action="playurl", url=url)
        xbmcplugin.addDirectoryItem(HANDLE, play_url, li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)


def prompt_url():
    """Open a keyboard, resolve the entered URL via Zeus Resolvers, then play."""
    kb = xbmcgui.Dialog().input(
        "Paste hoster URL (Streamtape / DDownload / ...)",
        type=xbmcgui.INPUT_ALPHANUM,
    )
    url = (kb or "").strip()
    if not url:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    if not url.lower().startswith(("http://", "https://")):
        xbmcgui.Dialog().notification(
            ADDON_NAME, "URL must start with http(s)://", xbmcgui.NOTIFICATION_WARNING, 4000
        )
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    _push_history(url)

    zeus = _zeus()
    if zeus is None:
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "script.module.zeusresolvers not installed",
            xbmcgui.NOTIFICATION_ERROR,
            5000,
        )
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    if not zeus.can_resolve(url):
        host = urllib.parse.urlparse(url).netloc
        xbmcgui.Dialog().ok(
            ADDON_NAME,
            f"Host not supported by Zeus Resolvers:\n\n[B]{host}[/B]\n\n"
            f"Supported hosts: {', '.join(zeus.supported_hosts())}",
        )
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    progress = xbmcgui.DialogProgressBG()
    progress.create(ADDON_NAME, f"Resolving {urllib.parse.urlparse(url).netloc}\u2026")
    resolved = None
    try:
        resolved = zeus.resolve(url)
    except Exception as exc:
        _log(f"resolve error: {exc}", xbmc.LOGERROR)
    finally:
        progress.close()

    if not resolved:
        xbmcgui.Dialog().notification(
            ADDON_NAME, "Could not resolve URL", xbmcgui.NOTIFICATION_ERROR, 4000
        )
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

    play_item = xbmcgui.ListItem(path=resolved)
    play_item.setArt({"icon": ADDON_ICON, "thumb": ADDON_ICON, "fanart": ADDON_FANART})
    info = play_item.getVideoInfoTag()
    info.setTitle(urllib.parse.urlparse(url).netloc)
    info.setMediaType("video")
    xbmc.Player().play(item=resolved, listitem=play_item)


def play_url(url):
    """Resolve and play a single URL via setResolvedUrl (history items)."""
    zeus = _zeus()
    resolved = None
    if zeus and zeus.can_resolve(url):
        try:
            resolved = zeus.resolve(url)
        except Exception as exc:
            _log(f"resolve error: {exc}", xbmc.LOGERROR)

    if not resolved:
        xbmcgui.Dialog().notification(
            ADDON_NAME, "Could not resolve URL", xbmcgui.NOTIFICATION_ERROR, 4000
        )
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    play_item = xbmcgui.ListItem(path=resolved)
    play_item.setArt({"icon": ADDON_ICON, "thumb": ADDON_ICON, "fanart": ADDON_FANART})
    info = play_item.getVideoInfoTag()
    info.setTitle(urllib.parse.urlparse(url).netloc)
    info.setMediaType("video")
    xbmcplugin.setResolvedUrl(HANDLE, True, play_item)


def play(idx, li_idx):
    items = _parse_items()
    it = items[int(idx)]
    link = it["links"][int(li_idx)]
    url = link["url"]

    zeus = _zeus()
    resolved = None
    if zeus is None:
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "script.module.zeusresolvers not installed",
            xbmcgui.NOTIFICATION_ERROR,
            5000,
        )
    else:
        try:
            if zeus.can_resolve(url):
                resolved = zeus.resolve(url)
            else:
                xbmcgui.Dialog().notification(
                    ADDON_NAME,
                    f"Host not supported: {urllib.parse.urlparse(url).netloc}",
                    xbmcgui.NOTIFICATION_WARNING,
                    4000,
                )
        except Exception as exc:
            _log(f"resolve error: {exc}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                f"Resolver error: {exc}",
                xbmcgui.NOTIFICATION_ERROR,
                5000,
            )

    if not resolved:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    play_item = xbmcgui.ListItem(path=resolved)
    play_item.setArt({"icon": ADDON_ICON, "thumb": ADDON_ICON, "fanart": ADDON_FANART})
    info = play_item.getVideoInfoTag()
    info.setTitle(f"{it['name']} - {link['name']}")
    info.setMediaType("video")
    xbmcplugin.setResolvedUrl(HANDLE, True, play_item)


def _capture_page_source(url):
    """Fetch ``url`` raw and pull out the bits that matter for diagnosing
    a Zeus Resolvers failure.

    Returns a list of ``(label, body)`` snippets ready for TextViewer.
    Captures (best-effort, regex-only):
        * HTTP status
        * Every ``getElementById('XXXlink').innerHTML = <expr>;`` JS line
          (Streamtape obfuscation lives here)
        * Every ``<div id="XXXlink" ...>...</div>`` body (Streamtape decoy)
        * Every ``<input name=... value=...>`` in the page (DDownloads form)
    """
    import re as _re
    import urllib.request as _ur

    snippets = []
    try:
        req = _ur.Request(url, headers={"User-Agent": USER_AGENT})
        with _ur.urlopen(req, timeout=20) as resp:
            status = resp.getcode()
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        snippets.append(("Fetch error", str(exc)))
        return snippets

    snippets.append(("HTTP status", str(status)))

    js_blocks = list(_re.finditer(
        r"getElementById\(\s*['\"]([A-Za-z0-9_]*link)['\"]\s*\)"
        r"\s*\.innerHTML\s*=\s*([^;]+);",
        html, _re.S,
    ))
    if js_blocks:
        body = "\n\n".join(
            f"[#{m.group(1)}]\n  {m.group(2).strip()[:600]}"
            for m in js_blocks
        )
        snippets.append((f"JS innerHTML assignments ({len(js_blocks)})", body))

    div_blocks = list(_re.finditer(
        r"<div[^>]*id\s*=\s*['\"]([A-Za-z0-9_]*link)['\"][^>]*>([^<]+)</div>",
        html, _re.I,
    ))
    if div_blocks:
        body = "\n".join(
            f"[#{m.group(1)}] {m.group(2).strip()[:300]}"
            for m in div_blocks
        )
        snippets.append((f"Hidden DIV bodies ({len(div_blocks)})", body))

    if "ddownload" in url.lower() or "ddl.to" in url.lower():
        fields = []
        for m in _re.finditer(
            r"""<input[^>]*name=["']([^"']+)["'][^>]*value=["']([^"']*)["']""",
            html, _re.I,
        ):
            fields.append(f"  {m.group(1)} = {m.group(2)}")
        for m in _re.finditer(
            r"""<input[^>]*value=["']([^"']*)["'][^>]*name=["']([^"']+)["']""",
            html, _re.I,
        ):
            fields.append(f"  {m.group(2)} = {m.group(1)}")
        if fields:
            # de-duplicate while preserving order
            seen = set()
            deduped = [f for f in fields if not (f in seen or seen.add(f))]
            snippets.append(("Form input fields", "\n".join(deduped)))

    return snippets


def diagnostics():
    """Self-test entry. Wraps everything in a try/except so any crash is
    visible in the TextViewer instead of being swallowed by Kodi."""
    try:
        _diagnostics_impl()
    except Exception as exc:
        import traceback as _tb
        body = (
            "[COLOR red][FATAL][/COLOR] diagnostics() crashed:\n\n"
            f"{exc}\n\n{_tb.format_exc()}"
        )
        try:
            xbmcgui.Dialog().textviewer("ZR Tester - Diagnostics", body)
        except Exception:
            pass
        try:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        except Exception:
            pass


def _diagnostics_impl():
    """Real diagnostics body. Loops over every host script.module.zeusresolvers
    claims to support and verifies its matcher recognises a probe URL.
    Optionally lets the user enter a live URL and runs the full
    ``resolve()`` flow end-to-end, reporting what came back. With "Capture
    page source" enabled, also dumps the raw obfuscation snippets so a
    failed probe is one paste away from a regex fix.
    """
    zeus = _zeus()
    lines = []
    if zeus is None:
        lines.append("[COLOR red][FAIL][/COLOR] script.module.zeusresolvers not installed.")
        xbmcgui.Dialog().textviewer("ZR Tester - Diagnostics", "\n".join(lines))
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    version = getattr(zeus, "__version__", "?")
    hosts = zeus.supported_hosts()

    lines.append(f"[B]Module:[/B] script.module.zeusresolvers v{version}")
    lines.append(f"[B]Supported hosts:[/B] {len(hosts)}")
    lines.append("")
    lines.append("[B]Matcher self-test (offline)[/B]")

    pass_count = 0
    fail_count = 0
    for host in hosts:
        probe = f"https://{host}/v/probe123"
        ok = bool(zeus.can_resolve(probe))
        if ok:
            pass_count += 1
            lines.append(f"  [COLOR lime][PASS][/COLOR] {host}")
        else:
            fail_count += 1
            lines.append(f"  [COLOR red][FAIL][/COLOR] {host}  (probe: {probe})")

    lines.append("")
    lines.append(
        f"Matcher: [COLOR lime]{pass_count} pass[/COLOR] / "
        f"[COLOR red]{fail_count} fail[/COLOR]"
    )

    # Optional live probe
    choice = xbmcgui.Dialog().select(
        "Live resolve probe",
        [
            "View results only (skip live probe)",
            "Probe URL  (resolve only)",
            "Capture + probe  (also dump page-source snippets)",
        ],
    )

    if choice in (1, 2):
        capture_mode = (choice == 2)
        url = xbmcgui.Dialog().input(
            "Paste a Streamtape / DDownload URL to probe",
            type=xbmcgui.INPUT_ALPHANUM,
        )
        url = (url or "").strip()
        if url:
            lines.append("")
            lines.append("[B]Live resolve probe[/B]")
            lines.append(f"Input : {url}")
            lines.append(f"Match : {bool(zeus.can_resolve(url))}")

            progress = xbmcgui.DialogProgressBG()
            progress.create(ADDON_NAME, "Probing\u2026")

            captured = []
            if capture_mode:
                progress.update(20, ADDON_NAME, "Capturing page source\u2026")
                captured = _capture_page_source(url)

            try:
                progress.update(60, ADDON_NAME, "resolve()\u2026")
                resolved = zeus.resolve(url)
            except Exception as exc:
                resolved = None
                lines.append(f"Error : {exc}")
            finally:
                progress.close()

            if resolved:
                shown = resolved if len(resolved) < 240 else resolved[:240] + "\u2026"
                lines.append("[COLOR lime][PASS][/COLOR] resolve() returned a URL")
                lines.append(f"Output: {shown}")
            else:
                lines.append("[COLOR red][FAIL][/COLOR] resolve() returned None")

            if capture_mode:
                lines.append("")
                lines.append("[B]Page source capture[/B]")
                if not captured:
                    lines.append("  (no diagnostic snippets extracted)")
                for label, body in captured:
                    lines.append(f"\n[COLOR yellow]>>> {label}[/COLOR]")
                    lines.append(body)

    xbmcgui.Dialog().textviewer("ZR Tester - Diagnostics", "\n".join(lines))
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)


def router():
    action = PARAMS.get("action")
    if action == "links":
        list_links(PARAMS.get("idx", "0"))
    elif action == "play":
        play(PARAMS.get("idx", "0"), PARAMS.get("li", "0"))
    elif action == "prompt":
        prompt_url()
    elif action == "history":
        list_history()
    elif action == "playurl":
        play_url(PARAMS.get("url", ""))
    elif action == "diagnostics":
        diagnostics()
    else:
        list_root()


if __name__ == "__main__":
    router()
