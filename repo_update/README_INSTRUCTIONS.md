# SALTS Addon - Adding to Zeus768 Repository

## Files Ready for Your Repo

### 1. Addon Folder
Copy the entire `plugin.video.salts` folder to your repo root:
```
/app/repo_update/plugin.video.salts/
```

### 2. Zip File  
Copy the zip to your `zips/plugin.video.salts/` folder:
```
/app/repo_update/zips/plugin.video.salts/plugin.video.salts-2.0.0.zip
```

### 3. Update addons.xml
Add this entry to your `addons.xml` file (before `</addons>`):

```xml
    <addon id="plugin.video.salts" version="2.0.0" name="SALTS - Stream All The Sources" provider-name="tknorris, zeus768">
        <requires>
            <import addon="xbmc.python" version="3.0.0"/>
            <import addon="script.module.resolveurl" version="5.1.0"/>
            <import addon="script.module.requests" version="2.25.0"/>
            <import addon="script.module.beautifulsoup4" version="4.9.0"/>
            <import addon="script.module.six" version="1.15.0"/>
        </requires>
        <extension point="xbmc.python.pluginsource" library="default.py">
            <provides>video</provides>
        </extension>
        <extension point="xbmc.service" library="service.py" start="startup"/>
        <extension point="xbmc.addon.metadata">
            <summary lang="en">Stream All The Sources - Modernized for Kodi 21+</summary>
            <description lang="en">SALTS v2.0.0 - Multi-source video addon with 13 torrent scrapers (1337x, YTS, EZTV, TorrentGalaxy, TPB, etc.), 4 streaming sites, Jackett/Prowlarr support, Real-Debrid/Premiumize/AllDebrid, and Trakt.tv integration. Original by tknorris, modernized by zeus768.</description>
            <platform>all</platform>
            <license>GPL-3.0-only</license>
            <website>https://github.com/zeus768/zeus768</website>
            <assets>
                <icon>icon.png</icon>
                <fanart>fanart.jpg</fanart>
            </assets>
        </extension>
    </addon>
```

### 4. Regenerate addons.xml.md5
After updating addons.xml, regenerate the MD5:
```bash
md5sum addons.xml | cut -d ' ' -f 1 > addons.xml.md5
```

## Final Repo Structure
```
zeus768/
├── plugin.video.salts/        <- NEW
│   ├── addon.xml
│   ├── default.py
│   ├── service.py
│   ├── icon.png
│   ├── fanart.jpg
│   ├── scrapers/
│   ├── salts_lib/
│   └── resources/
├── plugin.video.orion/
├── plugin.video.strikezone/
├── ... (other addons)
├── zips/
│   └── plugin.video.salts/    <- NEW
│       └── plugin.video.salts-2.0.0.zip
├── addons.xml                 <- UPDATE
└── addons.xml.md5             <- REGENERATE
```
