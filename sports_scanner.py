import requests
import re
import os
import sys

def scan_selcuk():
    print("\n🔍 SELCUK SPORTS TARANIYOR...")
    for i in range(1900, 2900):
        url = f"https://www.selcuksportshd{i}.xyz/"
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if r.status_code == 200 and "uxsyplayer" in r.text:
                print(f"✅ Selcuk bulundu: {url}")
                return r.text, url
        except:
            continue
    return None, None

def scan_cafe():
    print("\n🔍 SPOR CAFE TARANIYOR...")
    for i in range(14, 100):
        url = f"https://www.sporcafe{i}.xyz/"
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if r.status_code == 200 and "uxsyplayer" in r.text:
                print(f"✅ Spor Cafe bulundu: {url}")
                return r.text, url
        except:
            continue
    return None, None

def get_player_domain(html):
    match = re.search(r'https?://(main\.uxsyplayer[0-9a-zA-Z\-]+\.click)', html)
    return f"https://{match.group(1)}" if match else None

def get_base_url(html, source):
    if source == "selcuk":
        match = re.search(r'this\.baseStreamUrl\s*=\s*[\'"]([^\'"]+)', html)
    else:
        match = re.search(r'this\.adsBaseUrl\s*=\s*[\'"]([^\'"]+)', html)
    return match.group(1) if match else None

def build_m3u8(base_url, channel_ids, referer, source):
    links = []
    for cid in channel_ids:
        url = f"{base_url}{cid}/playlist.m3u8"
        print(f"  + {cid}")
        links.append((cid, url))
    return links

def save_m3u(links, filename, referer):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for cid, url in links:
            name = cid.replace("-", " ").title()
            f.write(f'#EXTINF:-1,{name}\n')
            f.write(f'#EXTVLCOPT:http-referrer={referer}\n')
            f.write(f'{url}\n\n')
    print(f"✅ {filename} kaydedildi")

# Kanal listeleri
SELCUK_IDS = [
    "selcukbeinsports1", "selcukbeinsports2", "selcukbeinsports3", "selcukbeinsports4", "selcukbeinsports5",
    "selcukbeinsportsmax1", "selcukbeinsportsmax2", "selcukssport", "selcukssport2", "selcuksmartspor",
    "selcuksmartspor2", "selcuktivibuspor1", "selcuktivibuspor2", "selcuktivibuspor3", "selcuktivibuspor4",
    "selcukbeinsportshaber", "selcukaspor", "selcukeurosport1", "selcukeurosport2", "selcuksf1",
    "selcuktabiispor", "selcuktrt1", "selcuktv8", "selcuktrtspor", "selcuktrtspor2", "selcukatv",
    "selcukdazn1", "selcukdazn2", "ssportplus1"
]

CAFE_IDS = [
    "sbeinsports-1", "sbeinsports-2", "sbeinsports-3", "sbeinsports-4", "sbeinsports-5",
    "sbeinsportsmax-1", "sbeinsportsmax-2", "sssport", "sssport2", "ssmartspor", "ssmartspor2",
    "stivibuspor-1", "stivibuspor-2", "stivibuspor-3", "stivibuspor-4", "sbeinsportshaber",
    "saspor", "seurosport1", "seurosport2", "sf1", "stabiispor", "strt1", "stv8",
    "strtspor", "strtspor2", "satv", "sdazn1", "sdazn2", "sssportplus1"
]

# Ana işlem
if len(sys.argv) > 1:
    mode = sys.argv[1]
else:
    mode = input("Seçim yapın (selcuk / cafe / all): ").strip().lower()

if mode in ["selcuk", "all"]:
    html, ref = scan_selcuk()
    if html:
        player = get_player_domain(html)
        if player:
            r = requests.get(f"{player}/index.php?id={SELCUK_IDS[0]}", headers={"User-Agent": "Mozilla/5.0", "Referer": ref})
            base = get_base_url(r.text, "selcuk")
            if base:
                links = build_m3u8(base, SELCUK_IDS, ref, "selcuk")
                save_m3u(links, "selcuk.m3u", ref)

if mode in ["cafe", "all"]:
    html, ref = scan_cafe()
    if html:
        player = get_player_domain(html)
        if player:
            links = []
            for cid in CAFE_IDS:
                try:
                    r = requests.get(f"{player}/index.php?id={cid}", headers={"User-Agent": "Mozilla/5.0", "Referer": ref}, timeout=5)
                    base = get_base_url(r.text, "cafe")
                    if base:
                        url = f"{base}{cid}/playlist.m3u8"
                        print(f"  + {cid}")
                        links.append((cid, url))
                except:
                    continue
            if links:
                save_m3u(links, "cafe.m3u", ref)
