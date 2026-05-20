# Salts Scrapers - Scrape All The Sources

Standalone scraper engine for the SALTS Kodi addon.

- **Addon ID:** `script.module.salts_scrapers`
- **Type:** `xbmc.python.module`
- **Author:** Zeus768
- **Version:** 1.0.0

## What this is

This is a Kodi *script module* (library) addon. It exposes a Python package
`scrapers` containing **120+ sources** (free streams, Stremio addons, torrent
sites, anime, asian drama, international, aggregators, ...).

It does **not** provide any UI of its own. The SALTS video addon
(`plugin.video.salts`) imports from this module to discover and search every
source.

## Why this exists

Previously every scraper lived inside `plugin.video.salts/scrapers/`. The
scrapers were extracted into this dedicated module so they can be updated,
versioned and re-used independently from the front-end addon.

## Installation

Install from zip in Kodi. SALTS 2.9.21+ declares this module as a dependency,
so Kodi will auto-install it from the same repository when SALTS is installed.

## Usage (from Python)

```python
from scrapers import get_all_scrapers, get_enabled_scrapers, ScraperVideo

video = ScraperVideo('movie', 'Inception', year='2010')
for scraper_cls in get_all_scrapers():
    scraper = scraper_cls()
    if scraper.is_enabled():
        sources = scraper.get_sources(video)
        ...
```

## License

GPL-3.0-only. Original SALTS author: tknorris. Scrapers extracted and packaged
into this module by Zeus768.
