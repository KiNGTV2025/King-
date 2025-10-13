#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright verbose XHR+runtime swKey yakalayıcı + doğrulayıcı.

- Ağ response ve requestleri tarar
- window/localStorage/sessionStorage/cookies inceler
- Ham candidate'ları found_swkeys_raw.txt'e yazar
- Doğrulama (HTTP 200 + JSON) sonuçlarını found_swkeys_valid.txt'e yazar
- Renkli log: [i]=mavi, [+]=yeşil, [-]=kırmızı
"""

import asyncio, aiohttp, json, re, os, traceback
from pathlib import Path
from playwright.async_api import async_playwright

# -------------------------- Ayarlar --------------------------
SAVE_DIR = Path("playwright_capture")
RAW_PATH = SAVE_DIR / "found_swkeys_raw.txt"
VALID_PATH = SAVE_DIR / "found_swkeys_valid.txt"

ACTIVE_DOMAINS = [
    "https://m.prectv55.lol",
    "https://m.prectv56.lol",
    "https://m.prectv59.lol",
    "https://m.prectv60.lol"
]

KEY_REGEX = re.compile(r'([A-Za-z0-9\/\-\._]{10,140})')
LIKELY_MARKERS = ("0H","00b","QWw","swKey","sw_key","apiKey","token")

TEST_PATHS = [
    "/api/movie/by/filtres/0/created/0/{key}/",
    "/api/channel/by/filtres/0/0/0/{key}/",
    "/api/serie/by/filtres/0/created/0/{key}/",
]

REQUEST_TIMEOUT = 10
VALIDATION_CONCURRENCY = 6
PAUSE_BETWEEN_VALIDATIONS = 0.4

# -------------------------- Yardımcılar --------------------------
def log(msg, lvl="i"):
    colors = {"i":"\033[34m", "+":"\033[32m", "-":"\033[31m"}
    print(f"{colors.get(lvl,'')}{lvl} {msg}\033[0m", flush=True)

def ensure_save_dir():
    SAVE_DIR.mkdir(exist_ok=True)

def likely_candidate_from_text(text):
    found = set()
    if not text:
        return found
    if not any(m in text for m in LIKELY_MARKERS):
        return found
    for m in KEY_REGEX.finditer(text):
        tok = m.group(1).strip()
        if len(tok) < 8 or len(tok) > 140 or " " in tok or "\t" in tok:
            continue
        if any(marker in tok for marker in LIKELY_MARKERS) or "/" in tok or "-" in tok:
            found.add(tok)
    return found

# -------------------------- Capture --------------------------
async def capture_page(domain, found_set):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True,
                                          args=["--no-sandbox","--disable-dev-shm-usage","--disable-gpu"])
        context = await browser.new_context()
        page = await context.new_page()

        # network events
        page.on("response", lambda r: [found_set.add(f"{domain}|resp|{c}") for c in likely_candidate_from_text(r.url)])
        page.on("request", lambda r: [found_set.add(f"{domain}|req|{c}") for c in likely_candidate_from_text(r.url)])

        try:
            await page.goto(domain, wait_until="load", timeout=30000)
        except:
            log(f"{domain} yüklenemedi", "-")

        await asyncio.sleep(4)  # XHR bekle

        # localStorage
        try:
            ls = await page.evaluate("() => JSON.stringify(Object.assign({}, window.localStorage))")
            for c in likely_candidate_from_text(ls or ""):
                found_set.add(f"{domain}|localStorage|{c}")
        except:
            pass

        # sessionStorage
        try:
            ss = await page.evaluate("() => JSON.stringify(Object.assign({}, window.sessionStorage))")
            for c in likely_candidate_from_text(ss or ""):
                found_set.add(f"{domain}|sessionStorage|{c}")
        except:
            pass

        # cookies
        try:
            cookies = await page.context.cookies()
            for c in likely_candidate_from_text(json.dumps(cookies)):
                found_set.add(f"{domain}|cookies|{c}")
        except:
            pass

        # window keys
        try:
            keys = await page.evaluate("() => Object.keys(window).slice(0,200)")
            for c in likely_candidate_from_text(json.dumps(keys)):
                found_set.add(f"{domain}|windowKeys|{c}")
        except:
            pass

        # common JS vars
        js_checks = ["window.__INITIAL_STATE__","window.__PRELOADED_STATE__","window.__DATA__","window.__CONFIG__","window.appConfig","window._env"]
        for var in js_checks:
            try:
                val = await page.evaluate(f"() => JSON.stringify({var})")
                for c in likely_candidate_from_text(val or ""):
                    found_set.add(f"{domain}|var|{c}")
            except:
                continue

        # clickable elements
        try:
            els = await page.query_selector_all("button, [onclick], a")
            limit = min(8, len(els))
            for i in range(limit):
                try:
                    await els[i].click(timeout=2000)
                    await asyncio.sleep(0.6)
                except:
                    continue
        except:
            pass

        await asyncio.sleep(1)
        await context.close()
        await browser.close()

# -------------------------- Validation --------------------------
async def validate_candidates(candidates):
    valid = []
    sem = asyncio.Semaphore(VALIDATION_CONCURRENCY)

    async def validate_one(session, raw_entry):
        parts = raw_entry.split("|",2)
        domain = parts[0] if len(parts) == 3 else None
        cand = parts[2] if len(parts) == 3 else parts[0]
        bases = [domain.rstrip("/")] if domain else []
        bases.extend(ACTIVE_DOMAINS)
        async with sem:
            for base in bases:
                for p in TEST_PATHS:
                    url = f"{base}{p.format(key=cand)}"
                    try:
                        async with session.get(url, timeout=REQUEST_TIMEOUT) as r:
                            txt = await r.text()
                            if r.status == 200 and txt and (txt.startswith("{") or txt.startswith("[")):
                                try:
                                    json.loads(txt)
                                    log(f"[VALID] {cand[:18]}... on {base}", "+")
                                    return {"key": cand, "base": base, "testurl": url}
                                except:
                                    continue
                    except:
                        continue
        return None

    async with aiohttp.ClientSession() as session:
        tasks = [validate_one(session, c) for c in candidates]
        for fut in asyncio.as_completed(tasks):
            res = await fut
            if res:
                valid.append(res)
            await asyncio.sleep(PAUSE_BETWEEN_VALIDATIONS)
    return valid

# -------------------------- Main --------------------------
async def main():
    ensure_save_dir()
    found_set = set()
    log("Başlıyor — Playwright swKey capture...", "i")

    tasks = [capture_page(domain, found_set) for domain in ACTIVE_DOMAINS]
    await asyncio.gather(*tasks)

    # save raw
    with open(RAW_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(found_set)))
    log(f"Ham candidate sayısı: {len(found_set)} -> {RAW_PATH}", "+")

    if not found_set:
        log("Hiç candidate bulunamadı — script sona eriyor.", "-")
        return

    # validate
    log("Doğrulama başlıyor...", "i")
    try:
        valid = await validate_candidates(found_set)
    except Exception as e:
        log(f"Validation error: {e}", "-")
        valid = []

    # save valid
    if valid:
        with open(VALID_PATH, "w", encoding="utf-8") as f:
            for v in valid:
                f.write(f"{v['key']}  # base={v['base']}  test={v['testurl']}\n")
        log(f"Geçerli key sayısı: {len(valid)} -> {VALID_PATH}", "+")
    else:
        log("Geçerli key bulunamadı.", "-")

if __name__ == "__main__":
    asyncio.run(main())
