#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright verbose XHR+runtime swKey yakalayıcı + doğrulayıcı.

- Tüm ağ response'larını ve request URL'lerini tarar
- page.evaluate ile window/localStorage/sessionStorage/cookies inceler
- buton/onclick tetiklemeleri yapar (limitli)
- Ham candidate'ları playwright_capture/found_swkeys_raw.txt'e yazar
- Doğrulama (HTTP 200 + JSON) sonuçlarını playwright_capture/found_swkeys_valid.txt'e yazar

NOT:
- Workflow içinde pip install playwright requests aiohttp olmalı.
- Çalıştırmadan önce repo'ya kaydet ve Actions çalıştır.
- Public repolarda otomatik commit yapma.
"""
import asyncio
import re
import os
from pathlib import Path
from playwright.async_api import async_playwright
import aiohttp
import json
import traceback
import time

SAVE_DIR = Path("playwright_capture")
RAW_PATH = SAVE_DIR / "found_swkeys_raw.txt"
VALID_PATH = SAVE_DIR / "found_swkeys_valid.txt"

# Domain aralığı (esnek tut)
CAND_BASES = [f"https://m.prectv{i}.lol" for i in range(50, 81)] + [f"https://m.prectv{i}.com" for i in range(50, 81)]
DEFAULT_TEST_BASES = ["https://m.prectv60.lol", "https://m.prectv59.lol", "https://m.prectv55.lol"]

# regex: swKey benzeri formatlar (esnek)
KEY_REGEX = re.compile(r'([A-Za-z0-9\/\-\._]{10,120})')
# daha seçici ek filtre stringleri — gereksiz çıkışları azaltmak için
LIKELY_MARKERS = ("0H", "00b", "QWw", "swKey", "sw_key", "SAYFA", "apiKey", "token")

# API test yolları (her base için denenecek)
TEST_PATHS = [
    "/api/movie/by/filtres/0/created/0/{key}/",
    "/api/channel/by/filtres/0/0/0/{key}/",
    "/api/serie/by/filtres/0/created/0/{key}/",
]

# Ağ / doğrulama ayarları
REQUEST_TIMEOUT = 10
VALIDATION_CONCURRENCY = 6
PAUSE_BETWEEN_VALIDATIONS = 0.6  # nazik olmak için bekleme

# yardımcılar
def ensure_save_dir():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

def likely_candidate_from_text(text):
    """Basit: text içinde marker varsa, regex ile candidate'ları döndür"""
    found = set()
    if not text:
        return found
    # hızlı kontrol: marker yoksa atla
    if not any(m in text for m in LIKELY_MARKERS):
        return found
    for m in KEY_REGEX.finditer(text):
        tok = m.group(1).strip()
        # ufak temizleme: boş/çok kısa/çok uzunları çıkar
        if len(tok) < 8 or len(tok) > 140:
            continue
        # token içinde boşluk olmasın
        if " " in tok or "\n" in tok or "\t" in tok:
            continue
        # ek filtre: en az bir marker substring içersin veya "/" varsa vs.
        if any(marker in tok for marker in LIKELY_MARKERS) or "/" in tok or "-" in tok:
            found.add(tok)
    return found

async def gather_active_domains():
    """Hangi domain'lerin 200 döndüğünü kontrol et ve döndür."""
    active = []
    async with aiohttp.ClientSession() as session:
        tasks = []
        for base in CAND_BASES:
            tasks.append(session.get(base, timeout=5))
        # sınırlı concurrency: gather ile birer birer run edelim (çok domain varsa timeout riski)
        for coro in asyncio.as_completed(tasks):
            try:
                resp = await coro
                url = str(resp.url)
                if resp.status == 200:
                    active.append(url)
                await resp.release()
            except Exception:
                continue
    return active

async def capture_from_page(page, found_set, domain):
    """Ağ eventlerini dinleyip response ve requestleri tarar; ayrıca runtime değişkenleri kontrol eder."""
    # response handler
    async def on_response(resp):
        try:
            url = resp.url
            # check url for candidate
            for c in likely_candidate_from_text(url):
                found_set.add(f"{domain}|url|{c}")
            # try to read text (may fail for binary)
            try:
                txt = await resp.text()
            except Exception:
                # fallback to body (binary) -> base64 not necessary here
                txt = None
            if txt:
                for c in likely_candidate_from_text(txt):
                    found_set.add(f"{domain}|resp|{c}")
        except Exception:
            # swallow errors in handler to avoid halting
            pass

    page.on("response", on_response)

    # request handler (URL query paramlarda token olabilir)
    async def on_request(req):
        try:
            url = req.url
            for c in likely_candidate_from_text(url):
                found_set.add(f"{domain}|req|{c}")
        except Exception:
            pass

    page.on("request", on_request)

    # navigate
    try:
        await page.goto(domain, wait_until="load", timeout=30000)
    except Exception:
        try:
            await page.goto(domain, wait_until="networkidle", timeout=30000)
        except Exception:
            return

    # biraz bekle ki XHR'ler gelsin
    await asyncio.sleep(6)

    # page.evaluate: local/session storage, window keys, some well known vars
    try:
        # localStorage
        try:
            ls = await page.evaluate("() => JSON.stringify(Object.assign({}, window.localStorage))")
            for c in likely_candidate_from_text(ls or ""):
                found_set.add(f"{domain}|localStorage|{c}")
        except Exception:
            pass
        # sessionStorage
        try:
            ss = await page.evaluate("() => JSON.stringify(Object.assign({}, window.sessionStorage))")
            for c in likely_candidate_from_text(ss or ""):
                found_set.add(f"{domain}|sessionStorage|{c}")
        except Exception:
            pass
        # cookies (context-level)
        try:
            cookies = await page.context.cookies()
            cookies_json = json.dumps(cookies)
            for c in likely_candidate_from_text(cookies_json):
                found_set.add(f"{domain}|cookies|{c}")
        except Exception:
            pass
        # window global keys (first 200 keys)
        try:
            keys = await page.evaluate("() => Object.keys(window).slice(0,200)")
            kjson = json.dumps(keys)
            for c in likely_candidate_from_text(kjson):
                found_set.add(f"{domain}|windowkeys|{c}")
        except Exception:
            pass
        # try some common runtime variables
        js_checks = [
            "window.__INITIAL_STATE__",
            "window.__PRELOADED_STATE__",
            "window.__DATA__",
            "window.__CONFIG__",
            "window.appConfig",
            "window._env"
        ]
        for var in js_checks:
            try:
                val = await page.evaluate(f"() => JSON.stringify({var})")
                for c in likely_candidate_from_text(val or ""):
                    found_set.add(f"{domain}|var|{c}")
            except Exception:
                pass
    except Exception:
        pass

    # try clicking up to N clickable elements to trigger more XHRs
    try:
        els = await page.query_selector_all("button, [onclick], a")
        limit = min(8, len(els))
        for i in range(limit):
            try:
                await els[i].click(timeout=2000)
                await asyncio.sleep(0.8)
            except Exception:
                continue
    except Exception:
        pass

    # final short wait
    await asyncio.sleep(2)

async def validate_candidates(candidates):
    """Async validate via aiohttp. Return list of valid keys."""
    valid = []
    sem = asyncio.Semaphore(VALIDATION_CONCURRENCY)

    async def validate_one(session, raw_entry):
        # raw_entry format: domain|where|candidate
        try:
            parts = raw_entry.split("|", 2)
            if len(parts) == 3:
                domain, where, cand = parts
            else:
                # fallback
                domain = None
                cand = raw_entry
            cand = cand.strip()
            # form list of bases to try: discovered domain (if any) + defaults
            bases = []
            if domain and domain.startswith("http"):
                bases.append(domain.rstrip("/"))
            bases.extend(DEFAULT_TEST_BASES)
            async with sem:
                for base in bases:
                    for p in TEST_PATHS:
                        test_url = f"{base}{p.format(key=cand)}"
                        try:
                            async with session.get(test_url, timeout=REQUEST_TIMEOUT) as resp:
                                text = None
                                try:
                                    text = await resp.text()
                                except Exception:
                                    pass
                                if resp.status == 200 and text:
                                    # check if JSON-like
                                    t = text.strip()
                                    if t.startswith("{") or t.startswith("["):
                                        # simple sanity: parse
                                        try:
                                            _ = json.loads(t)
                                            print(f"[VALID] {cand[:18]}... on {base} (200 json)")
                                            return cand, base, test_url
                                        except Exception:
                                            # even if not parseable, accept 200 as potential
                                            print(f"[VALID?] {cand[:18]}... on {base} (200, non-json)")
                                            return cand, base, test_url
                                # if 401/403 it's invalid for this key-base combo
                        except Exception:
                            await asyncio.sleep(0.1)
                # none matched
            return None
        except Exception:
            return None

    async with aiohttp.ClientSession() as session:
        tasks = [validate_one(session, c) for c in candidates]
        for fut in asyncio.as_completed(tasks):
            try:
                res = await fut
                if res:
                    cand, base, testurl = res
                    valid.append({"key": cand, "base": base, "testurl": testurl})
                # polite small pause
                await asyncio.sleep(PAUSE_BETWEEN_VALIDATIONS)
            except Exception:
                pass
    return valid

async def main():
    ensure_save_dir()
    found_set = set()
    print("[i] Başlıyor — XHR & runtime capture (Playwright)")

    # 1) hangi domain'ler aktif bak (hızlı)
    print("[i] Aktif domain taraması başlıyor...")
    active_domains = []
    try:
        active_domains = await gather_active_domains()
    except Exception as e:
        print("[!] domain taramada hata:", e)
    if not active_domains:
        print("[x] Aktif domain bulunamadı, yine de default domaini deneyeceğim.")
        active_domains = DEFAULT_TEST_BASES

    print(f"[i] Aktif domain sayısı: {len(active_domains)}")

    # 2) playwriht ile her aktif domain'i tara ve ağ event'lerinden candidate topla
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True,
                                              args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
                extra_http_headers={"Referer": "https://twitter.com/", "Accept-Language": "en-US,en;q=0.9"}
            )
            page = await context.new_page()

            for domain in active_domains:
                try:
                    await capture_from_page(page, found_set, domain)
                except Exception as e:
                    print("[!] capture error for", domain, e)
                    traceback.print_exc()

            await context.close()
            await browser.close()
    except Exception as e:
        print("[!] Playwright error:", e)
        traceback.print_exc()

    # 3) save raw candidates (unique)
    found_list = sorted(found_set)
    with open(RAW_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(found_list))
    print(f"[i] Ham candidate sayısı: {len(found_list)} -> {RAW_PATH}")

    if not found_list:
        print("[i] Hiç candidate bulunamadı — script sona eriyor.")
        return

    # 4) doğrulama
    print("[i] Doğrulama başlıyor (nazik şekilde)...")
    try:
        valid = await validate_candidates(found_list)
    except Exception as e:
        print("[!] validation error:", e)
        valid = []

    # 5) yaz
    if valid:
        with open(VALID_PATH, "w", encoding="utf-8") as f:
            for v in valid:
                f.write(f"{v['key']}  # base={v['base']}  test={v['testurl']}\n")
        print(f"[i] Geçerli key sayısı: {len(valid)} -> {VALID_PATH}")
    else:
        print("[i] Geçerli key bulunamadı.")

if __name__ == "__main__":
    asyncio.run(main())
