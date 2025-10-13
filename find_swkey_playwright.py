#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gelişmiş RecTV swKey bulucu — Playwright (verbose)
- Tüm network request/response'ları kaydeder (text/json)
- page source, localStorage, sessionStorage, cookies, window keys toplar
- sayfadaki onclick/button click tetiklemeleri uygular
- tüm bulunan candidate'ları regex ile arayıp found_swkeys.txt'ye yazar

Kullanım:
  pip install playwright
  python -m playwright install
  python find_swkey_playwright_verbose.py
"""
import re
import os
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

MAIN_URL = "https://m.prectv60.lol"
OUTDIR = Path("playwright_capture")
OUTDIR.mkdir(exist_ok=True)

# Regex candidate'lar
KEY_REGEX = re.compile(
    r'([A-Za-z0-9]{6,64}/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})'
)
SWKEY_VAR_REGEX = re.compile(r'(?i)(swkey|sw_key|sw-key|SAYFA|apiKey|token|key)["\':=\s]*["\']?([A-Za-z0-9\/\-\._]{8,120})["\']?')

found = set()

def save_text(filename, text):
    path = OUTDIR / filename
    with open(path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(text)
    return str(path)

def try_extract_from_text(text):
    if not text:
        return
    for m in KEY_REGEX.finditer(text):
        found.add(m.group(1))
    for m in SWKEY_VAR_REGEX.finditer(text):
        found.add(m.group(2))

def main():
    print("[i] Başlıyor — Playwright (verbose capture)")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # headless=False istersen GUI aç
        context = browser.new_context(
            user_agent="okhttp/4.12.0",
            extra_http_headers={"Referer": "https://twitter.com/"},
            ignore_https_errors=True,
        )
        page = context.new_page()

        # Kaydedici sayaçları
        req_count = 0
        resp_count = 0

        # request kaydet
        def on_request(req):
            nonlocal req_count
            req_count += 1
            info = {
                "method": req.method,
                "url": req.url,
                "headers": dict(req.headers),
            }
            # post verisi al (varsa)
            try:
                post = req.post_data
                if post:
                    info["post_data"] = post
            except Exception:
                pass
            fname = f"request_{req_count:04d}.json"
            save_text(fname, json.dumps(info, ensure_ascii=False, indent=2))
        page.on("request", on_request)

        # response kaydet
        def on_response(resp):
            nonlocal resp_count
            resp_count += 1
            try:
                url = resp.url
                status = resp.status
                headers = dict(resp.headers)
                # body almak riskli olabilir (binary). önce text() dene:
                body_text = None
                try:
                    body_text = resp.text()
                except Exception:
                    try:
                        # binary -> base64 fallback
                        b = resp.body()
                        import base64
                        body_text = base64.b64encode(b).decode("ascii")
                    except Exception:
                        body_text = None
                info = {
                    "url": url,
                    "status": status,
                    "headers": headers,
                    "body_saved_as": None
                }
                fname = f"response_{resp_count:04d}.txt"
                if body_text:
                    path = save_text(fname, body_text)
                    info["body_saved_as"] = fname
                    # metin içinde candidate ara
                    try_extract_from_text(body_text)
                # url içinde candidate ara
                try_extract_from_text(url)
                # kaydet
                save_text(f"response_meta_{resp_count:04d}.json", json.dumps(info, ensure_ascii=False, indent=2))
            except Exception as e:
                # ignore
                pass
        page.on("response", on_response)

        # navigate et
        print(f"[i] {MAIN_URL} adresine gidiliyor...")
        page.goto(MAIN_URL, wait_until="networkidle", timeout=45000)

        # ekstra bekleme - arka XHR'lerin tamamlanması için
        wait_seconds = 12
        print(f"[i] Ek bekleme: {wait_seconds}s")
        time.sleep(wait_seconds)

        # sayfa içeriğini kaydet
        html = page.content()
        save_text("page_source.html", html)
        try_extract_from_text(html)

        # localStorage, sessionStorage, cookies, window keys çek
        try:
            ls = page.evaluate("() => Object.assign({}, window.localStorage)")
            if ls:
                save_text("localStorage.json", json.dumps(ls, ensure_ascii=False, indent=2))
                try_extract_from_text(json.dumps(ls))
        except Exception:
            pass

        try:
            ss = page.evaluate("() => Object.assign({}, window.sessionStorage)")
            if ss:
                save_text("sessionStorage.json", json.dumps(ss, ensure_ascii=False, indent=2))
                try_extract_from_text(json.dumps(ss))
        except Exception:
            pass

        try:
            cookies = context.cookies()
            save_text("cookies.json", json.dumps(cookies, ensure_ascii=False, indent=2))
            try_extract_from_text(json.dumps(cookies))
        except Exception:
            pass

        # window anahtarlarını listele (çok büyük olabilir; sadece anahtarları al)
        try:
            window_keys = page.evaluate("() => Object.keys(window).slice(0,500)")
            save_text("window_keys.json", json.dumps(window_keys, ensure_ascii=False, indent=2))
            try_extract_from_text(json.dumps(window_keys))
        except Exception:
            pass

        # sayfadaki onclick attribute'lu elementleri bulup tıkla (JS olayları tetiklenebilir)
        try:
            clickable = page.query_selector_all("[onclick], button, a")
            print(f"[i] onclick/button/a sayısı: {len(clickable)} — ilk 12'si tıklanıyor (güvenlik için limit)")
            for idx, el in enumerate(clickable[:12]):
                try:
                    el.click(timeout=2000)
                    time.sleep(0.8)
                except Exception:
                    pass
        except Exception:
            pass

        # tekrar biraz bekle, yeni XHR/response'ları yakala
        time.sleep(6)

        # ek script src'lerini indir (page'de bulunan script src attribute'lerini indir)
        scripts = page.query_selector_all("script")
        print(f"[i] script tag sayısı: {len(scripts)}; kaynaklar indiriliyor (limit 40).")
        script_srcs = []
        for s in scripts:
            try:
                src = s.get_attribute("src")
                if src:
                    # tam url oluştur
                    if src.startswith("http"):
                        script_srcs.append(src)
                    else:
                        script_srcs.append(page.url.rstrip("/") + "/" + src.lstrip("/"))
            except Exception:
                pass

        for i, src in enumerate(script_srcs[:40], start=1):
            try:
                resp = context.request.get(src)
                text = resp.text()
                save_text(f"script_{i:03d}.js", text)
                try_extract_from_text(text)
            except Exception:
                continue

        # Son olarak bulunan candidate'ları kaydet
        if found:
            print(f"[+] Toplam bulunan candidate: {len(found)}")
            with open(OUTDIR / "found_swkeys.txt", "w", encoding="utf-8") as f:
                for k in sorted(found):
                    f.write(k + "\n")
            print(f"[i] Kaydedildi: {OUTDIR / 'found_swkeys.txt'}")
        else:
            print("[!] Hiç candidate bulunamadı (verbose). Yine de ham kayıtları incele.")

        # kapat
        context.close()
        browser.close()

    print("[i] Bitti. Klasörü kontrol et:", OUTDIR)

if __name__ == "__main__":
    main()
