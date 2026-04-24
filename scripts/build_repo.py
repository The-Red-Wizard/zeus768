#!/usr/bin/env python3
"""Repackage Kodi addons and regenerate /app/addons.xml(+.md5).

Usage:
    python3 scripts/build_repo.py [addon_id1 addon_id2 ...]

If no addon ids are provided, ALL top-level ``<addon_id>/`` folders that
contain an ``addon.xml`` are packaged.

For each target:
    * reads ``<root>/<addon_id>/addon.xml`` to learn its version
    * writes ``<root>/zips/<addon_id>/<addon_id>-<version>.zip``
      (prunes older versions of the same addon)
    * re-copies ``icon.png`` / ``fanart.jpg`` next to the zip (for Kodi
      repository browsing)

Finally regenerates:
    * /app/addons.xml         (concatenation of every addon.xml under zips)
    * /app/addons.xml.md5     (md5 of the concatenated manifest)

Excludes: __pycache__, *.pyc, .git, .gitignore, .DS_Store, *.zip
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIPS = ROOT / "zips"

EXCLUDE_DIRS = {"__pycache__", ".git", ".github", ".vscode", "node_modules"}
EXCLUDE_FILE_EXT = {".pyc", ".pyo"}
EXCLUDE_FILE_NAMES = {".DS_Store", ".gitignore"}


def is_addon_dir(p: Path) -> bool:
    return p.is_dir() and (p / "addon.xml").exists()


def addon_version(addon_xml: Path) -> str:
    """Regex-read the ``version="..."`` from the root ``<addon>`` tag.

    Using regex avoids failures on addon descriptions that include raw
    ampersands or other loose characters in ``<description>`` bodies.
    """
    txt = addon_xml.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<addon\b[^>]*\bversion\s*=\s*\"([^\"]+)\"", txt)
    if not m:
        raise ValueError(f"No version attribute in {addon_xml}")
    return m.group(1)


def zip_addon(addon_dir: Path) -> Path:
    addon_id = addon_dir.name
    version = addon_version(addon_dir / "addon.xml")
    out_dir = ZIPS / addon_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clean previous zips of this addon (keep icon/fanart).
    for old in out_dir.glob(f"{addon_id}-*.zip"):
        old.unlink()

    target = out_dir / f"{addon_id}-{version}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(addon_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for fname in files:
                if fname in EXCLUDE_FILE_NAMES:
                    continue
                if Path(fname).suffix in EXCLUDE_FILE_EXT:
                    continue
                fp = Path(root) / fname
                arc = Path(addon_id) / fp.relative_to(addon_dir)
                zf.write(fp, arc.as_posix())

    # Copy icon/fanart alongside zip for repo browsing if present.
    for art in ("icon.png", "fanart.jpg"):
        src = addon_dir / art
        if src.exists():
            shutil.copy2(src, out_dir / art)

    print(f"  packed {target.relative_to(ROOT)}  ({target.stat().st_size:,} bytes)")
    return target


def rebuild_manifest() -> None:
    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', "<addons>", ""]
    for addon_dir in sorted(p for p in ROOT.iterdir() if is_addon_dir(p)):
        ax = (addon_dir / "addon.xml").read_text(encoding="utf-8")
        # Strip any leading XML declaration inside the addon file.
        ax = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", ax).strip()
        lines.append(ax)
        lines.append("")
    lines.append("</addons>")
    manifest = "\n".join(lines) + "\n"
    (ROOT / "addons.xml").write_text(manifest, encoding="utf-8")
    (ROOT / "addons.xml.md5").write_text(
        hashlib.md5(manifest.encode("utf-8")).hexdigest() + "\n",
        encoding="utf-8",
    )
    print(f"  wrote addons.xml ({len(manifest):,} bytes) + addons.xml.md5")


def main(argv: list[str]) -> int:
    if argv:
        targets = [ROOT / aid for aid in argv]
    else:
        targets = [p for p in ROOT.iterdir() if is_addon_dir(p)]

    missing = [t for t in targets if not is_addon_dir(t)]
    if missing:
        print("ERROR: not a valid addon dir:", ", ".join(str(m) for m in missing))
        return 1

    print(f"Packaging {len(targets)} addon(s)...")
    for t in targets:
        zip_addon(t)

    print("Rebuilding manifest...")
    rebuild_manifest()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
