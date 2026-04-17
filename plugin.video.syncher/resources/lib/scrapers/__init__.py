# -*- coding: utf-8 -*-
"""Syncher - Scraper base class and utilities"""

import re

VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.mpg', '.mpeg', '.ts', '.webm']

def parse_quality(name):
    """Extract quality from a release name"""
    name = name.upper()
    if any(x in name for x in ['2160P', '4K', 'UHD']):
        return '4K'
    if any(x in name for x in ['1080P', '1080I', 'FULLHD', 'FULL HD']):
        return '1080p'
    if any(x in name for x in ['720P', 'HD']):
        return '720p'
    if any(x in name for x in ['480P', 'HDTV', 'SDTV', 'DVDRIP', 'BDRIP', 'BRRIP', 'R5', 'SCREAM']):
        return 'SD'
    return 'SD'

def parse_info(name):
    """Extract codec/source info from release name"""
    info = []
    name_upper = name.upper()
    if 'BLURAY' in name_upper or 'BLU-RAY' in name_upper:
        info.append('BluRay')
    elif 'WEB-DL' in name_upper or 'WEBDL' in name_upper:
        info.append('WEB-DL')
    elif 'WEBRIP' in name_upper or 'WEB-RIP' in name_upper:
        info.append('WEBRip')
    elif 'HDTV' in name_upper:
        info.append('HDTV')
    elif 'DVDRIP' in name_upper:
        info.append('DVDRip')

    if 'X265' in name_upper or 'H265' in name_upper or 'H.265' in name_upper or 'HEVC' in name_upper:
        info.append('x265')
    elif 'X264' in name_upper or 'H264' in name_upper or 'H.264' in name_upper:
        info.append('x264')

    if 'HDR' in name_upper:
        info.append('HDR')
    if 'REMUX' in name_upper:
        info.append('REMUX')
    if 'ATMOS' in name_upper:
        info.append('Atmos')
    elif 'DTS-HD' in name_upper:
        info.append('DTS-HD')
    elif 'DTS' in name_upper:
        info.append('DTS')
    elif 'DD5' in name_upper or 'AC3' in name_upper:
        info.append('DD5.1')

    return ' | '.join(info)

def clean_title(title):
    """Clean title for comparison"""
    if not title:
        return ''
    title = re.sub(r'[\W_]+', ' ', title.lower()).strip()
    return title

def match_title(scraped_name, title, year=None):
    """Check if a scraped name matches the expected title/year"""
    clean_scraped = clean_title(scraped_name)
    clean_expected = clean_title(title)

    if clean_expected in clean_scraped:
        if year and str(year) in scraped_name:
            return True
        elif not year:
            return True
    return False

def match_episode(scraped_name, title, season, episode):
    """Check if scraped name matches TV show episode"""
    clean_scraped = clean_title(scraped_name)
    clean_expected = clean_title(title)

    if clean_expected not in clean_scraped:
        return False

    # Check S01E01 pattern
    pattern = r's0*%s\s*e0*%s' % (season, episode)
    if re.search(pattern, clean_scraped, re.I):
        return True

    # Check season.episode pattern
    pattern2 = r'%sx%s' % (season, episode.zfill(2))
    if pattern2 in clean_scraped:
        return True

    return False

def extract_magnet_hash(magnet):
    """Extract info hash from a magnet link"""
    match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
    if match:
        return match.group(1).lower()
    match = re.search(r'btih:([a-zA-Z2-7]{32})', magnet)
    if match:
        import base64
        try:
            decoded = base64.b32decode(match.group(1).upper())
            return decoded.hex().lower()
        except:
            pass
    return None
