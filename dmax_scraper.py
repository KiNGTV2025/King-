#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DMAX scraper (M3U üretir ve Dropbox'a yükler)
- all.m3u       → ./DMAX/all.m3u ve Dropbox /DMAX/all.m3u
- programlar/*.m3u → ./DMAX/programs/<slug>.m3u ve Dropbox /DMAX/programs/<slug>.m3u
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from requests.adapters import HTTPAdapter, Retry
from slugify import slugify
import dropbox

# ============================
# ÇIKTI KONUMU
# ============================
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "DMAX"
PROGRAMS_DIR = OUTPUT_DIR / "programs"

# ============================
# DROPBOX
# ============================
DROPBOX_REFRESH_TOKEN = os.environ.get("DROPBOX_REFRESH_TOKEN")

def upload_to_dropbox(local_path: str, dropbox_path: str):
    """Dosyayı Dropbox'a yükler."""
    if not DROPBOX_REFRESH_TOKEN:
        logging.warning("DROPBOX_REFRESH_TOKEN tanımlı değil, yükleme yapılmadı.")
        return
    try:
        dbx = dropbox.Dropbox(DROPBOX_REFRESH_TOKEN)
        with open(local_path, "rb") as f:
            dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
        log.info("Dropbox'a yüklendi: %s", dropbox_path)
    except Exception as e:
        log.error("Dropbox yükleme hatası: %s", e)

# ============================
# M3U YARDIMCILARI
# ============================

def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    tmp.replace(path)

def _safe_series_filename(name: str) -> str:
    return slugify((name or "dizi").lower()) + ".m3u"

def _pick_stream_url(ep: Dict[str, Any]) -> Optional[str]:
    url = ep.get("stream_url")
    if url:
        return url
    cands = ep.get("stream_url_candidates")
    if isinstance(cands, (list, tuple)) and cands:
        return cands[0]
    return None

# ============================
# M3U OLUŞTURMA
# ============================

def create_m3us(data: List[Dict[str, Any]], master: bool = False):
    _ensure_dir(PROGRAMS_DIR)
    master_lines: List[str] = ["#EXTM3U"] if master else []

    for serie in data:
        episodes = serie.get("episodes") or []
        if not episodes:
            continue

        series_name = (serie.get("name") or "Bilinmeyen Seri").strip()
        series_logo = (serie.get("img") or "").strip()
        plist_name = _safe_series_filename(series_name)
        plist_path = PROGRAMS_DIR / plist_name

        lines = ["#EXTM3U"]
        for ep in episodes:
            stream = _pick_stream_url(ep)
            if not stream:
                continue
            ep_name = ep.get("name") or "Bölüm"
            logo_for_line = series_logo or ep.get("img") or ""
            group = series_name.replace('"', "'")
            lines.append(f'#EXTINF:-1 tvg-logo="{logo_for_line}" group-title="{group}",{ep_name}')
            lines.append(stream)

        if len(lines) > 1:
            _atomic_write(plist_path, "\n".join(lines) + "\n")
            upload_to_dropbox(plist_path, f"/DMAX/programs/{plist_name}")
            if master:
                master_lines.append(f'#EXTINF:-1 tvg-logo="{series_logo}", {series_name}')
                master_lines.append(f'programs/{plist_name}')

    if master:
        master_path = OUTPUT_DIR / "all.m3u"
        _atomic_write(master_path, "\n".join(master_lines) + "\n")
        upload_to_dropbox(master_path, "/DMAX/all.m3u")

def create_single_m3u(data: List[Dict[str, Any]], custom_name: str = "all"):
    _ensure_dir(OUTPUT_DIR)
    master_path = OUTPUT_DIR / f"{custom_name}.m3u"

    lines = ["#EXTM3U"]
    for serie in data:
        series_name = (serie.get("name") or "Bilinmeyen Seri").strip()
        series_logo = (serie.get("img") or "").strip()
        episodes = serie.get("episodes") or []
        for ep in episodes:
            stream = _pick_stream_url(ep)
            if not stream:
                continue
            ep_name = ep.get("name") or "Bölüm"
            logo_for_line = series_logo or ep.get("img") or ""
            group = series_name.replace('"', "'")
            lines.append(f'#EXTINF:-1 tvg-logo="{logo_for_line}" group-title="{group}",{ep_name}')
            lines.append(stream)

    _atomic_write(master_path, "\n".join(lines) + "\n")
    upload_to_dropbox(master_path, f"/DMAX/{custom_name}.m3u")

# ============================
# SAVE OUTPUTS
# ============================

def save_outputs_only_m3u(data: Dict[str, Any]):
    programs = data.get("programs", [])
    try:
        create_single_m3u(programs, "all")
        create_m3us(programs, master=True)
        log.info("Tüm M3U dosyaları oluşturuldu ve Dropbox /DMAX altında yüklendi.")
    except Exception as e:
        log.error("M3U oluşturma hatası: %s", e)

# ============================
# Geri kalan scraper kodları
# (get_soup_from_post, get_soup_from_get, get_all_programs, run vb.)
# ============================

# … önceki kodları buraya aynen ekleyin …

def parse_args(argv: List[str]) -> Tuple[int, int]:
    start, end = 0, 0
    if len(argv) >= 2:
        try:
            start = int(argv[1])
        except Exception:
            pass
    if len(argv) >= 3:
        try:
            end = int(argv[2])
        except Exception:
            pass
    return start, end

def main():
    start, end = parse_args(sys.argv)
    data = run(start=start, end=end)
    save_outputs_only_m3u(data)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )
    global log
    log = logging.getLogger("dmax-scraper")
    main()
