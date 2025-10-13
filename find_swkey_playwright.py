#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RecTV swKey bulucu — Playwright sürümü
Kullanım:
  pip install -r requirements.txt
  python -m playwright install
  python find_swkey_playwright.py

Not: Playwright gerçek bir tarayıcı başlatır (headless by default).
"""
import re
import time
from playwright.sync_api import sync_playwright

MAIN_URL = "https://m.prectv60.lol"
# Esnek key regex (kotlin örneğindeki biçime benzer)
KEY_REGEX = re.compile(
    r'([A-Za-z0-9]{6,64}/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})'
)
# Alternatif: değişken adıyla saklanan key'ler
SWKEY_VAR_REGEX = re.compile(r'(?i)(swkey|sw_key|sw-key|SAYFA|apiKey|key)["\':=\s]*["\']?([A-Za-z0-9\/\-]{10,80})["\']?')


def extract_from_text(text):
    found = set()
    if not text:
        return found
    for m in KEY_REGEX.finditer(text):
        found.add(m.group(1))
    for m in SWKEY_VAR_REGEX.finditer(text):
        found.add(m.group(2))
    return found


def main():
    found_keys = set()
    print("[i] Playwright başlatılıyor...")
    with sync_playwright() as p:
        # Chromium kullan; dilersen firefox/webkit değiştir
        browser = p.chromium.launch(headless=True)
        # Başlıkları taklit et (Kotlin'de kullanılanlara benzer)
        context = browser.new_context(
            user_agent="okhttp/4.12.0",
            extra_http_headers={"Referer": "https://twitter.com/", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
        )
        page = context.new_page()

        # Ağ cevaplarını dinle
        def on_response(response):
            try:
                url = response.url
                text = None
                try:
                    text = response.text()
                except Exception:
                    return
                if text:
                    for m in KEY_REGEX.finditer(url):
                        found_keys.add(m.group(1))
                    for k in extract_from_text(text):
                        found_keys.add(k)
            except Exception:
                return

        page.on("response", on_response)

        print(f"[i] {MAIN_URL} adresine gidiliyor...")
        page.goto(MAIN_URL, wait_until="networkidle", timeout=30000)

        print("[i] Sayfa yüklendi — ek bekleme (10s) JS/XHR için...")
        time.sleep(10)

        page_html = page.content()
        for k in extract_from_text(page_html):
            found_keys.add(k)

        scripts = page.query_selector_all("script")
        script_srcs = []
        for s in scripts:
            src = s.get_attribute("src")
            if src:
                script_srcs.append(src)

        limit = 40
        for i, src in enumerate(script_srcs[:limit]):
            try:
                script_url = page.url.rstrip("/") + "/" + src.lstrip("/")
                resp = context.request.get(script_url)
                if resp.ok:
                    txt = resp.text()
                    for k in extract_from_text(txt):
                        found_keys.add(k)
            except Exception:
                continue

        context.close()
        browser.close()

    if found_keys:
        print("\n[+] Bulunan candidate key(ler):")
        for k in sorted(found_keys):
            print("  -", k)
        with open("found_swkeys.txt", "w", encoding="utf-8") as f:
            for k in sorted(found_keys):
                f.write(k + "\n")
        print("\n[i] Kaydedildi: found_swkeys.txt")
    else:
        print("\n[!] Hiç key bulunamadı. Muhtemel sebepler:")
        print("    - Token tamamen runtime'da (XHR ile oluşturuluyor) ve JS sonucu şifreleniyor.")
        print("    - Site daha karmaşık anti-bot kullanıyor; header / cookie gereksinimi var.")
        print("    - Farklı host/alt domain üzerinde token oluşturuluyor (ek domainleri kontrol et).")


if __name__ == "__main__":
    main()
