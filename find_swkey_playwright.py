import asyncio
import aiohttp
import os
from playwright.async_api import async_playwright

SAVE_DIR = "playwright_capture"
RAW_PATH = os.path.join(SAVE_DIR, "found_swkeys_raw.txt")
VALID_PATH = os.path.join(SAVE_DIR, "found_swkeys_valid.txt")

# 50–80 arası domainleri dene (.lol ve .com)
BASE_DOMAINS = [f"m.prectv{i}.lol" for i in range(50, 81)] + [f"m.prectv{i}.com" for i in range(50, 81)]

API_TEMPLATE = "https://m.prectv60.lol/api/movie/by/filtres/0/created/0/{}/c3c5bd17-e37b-4b94-a944-8a3688a30452/"


# --- Aşama 1: Aktif domainleri bul ---
async def check_domain(session, domain):
    url = f"https://{domain}"
    try:
        async with session.get(url, timeout=5) as resp:
            if resp.status == 200:
                print(f"[+] Aktif domain: {url}")
                return url
    except:
        pass
    return None


async def find_active_domains():
    print("[i] Domain kontrolü başlıyor...")
    async with aiohttp.ClientSession() as session:
        tasks = [check_domain(session, d) for d in BASE_DOMAINS]
        results = await asyncio.gather(*tasks)
        active = [r for r in results if r]
    print(f"[i] Aktif domain sayısı: {len(active)}")
    return active


# --- Aşama 2: Script’lerden anahtarları çıkar ---
async def scrape_domain(page, domain):
    print(f"[→] {domain} taranıyor...")
    try:
        await page.goto(domain, timeout=30000)
        await page.wait_for_timeout(12000)
        scripts = await page.locator("script").all_inner_texts()
        found = []
        for text in scripts:
            for line in text.splitlines():
                if any(k in line for k in ("0H", "00b", "QWw", "swKey")):
                    line = line.strip()
                    if len(line) > 8:
                        found.append(line)
        return found
    except Exception as e:
        print(f"[!] {domain} hata: {e}")
        return []


# --- Aşama 3: Anahtar doğrulama (HTTP 200/401 testi) ---
async def validate_key(session, key):
    url = API_TEMPLATE.format(key.strip())
    try:
        async with session.get(url, timeout=8) as resp:
            if resp.status == 200:
                print(f"[✔] Geçerli anahtar: {key[:10]}... ({resp.status})")
                return key
            else:
                print(f"[✖] {key[:10]}... -> {resp.status}")
    except:
        print(f"[!] {key[:10]}... -> bağlantı hatası")
    return None


# --- Ana süreç ---
async def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    all_found = []

    # 1️⃣ Aktif domainleri bul
    active_domains = await find_active_domains()
    if not active_domains:
        print("[x] Hiç aktif domain bulunamadı.")
        return

    # 2️⃣ Domainleri tara
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        page = await browser.new_page()
        for domain in active_domains:
            found = await scrape_domain(page, domain)
            if found:
                print(f"[+] {domain} -> {len(found)} anahtar bulundu.")
                all_found.extend(found)
            else:
                print(f"[-] {domain} -> anahtar bulunamadı.")
        await browser.close()

    # 3️⃣ Bulunanları kaydet (raw)
    with open(RAW_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(all_found))
    print(f"\n[i] {len(all_found)} ham anahtar kaydedildi → {RAW_PATH}")

    # 4️⃣ Doğrulama
    print("\n[i] Doğrulama başlıyor...")
    async with aiohttp.ClientSession() as session:
        tasks = [validate_key(session, k) for k in all_found]
        results = await asyncio.gather(*tasks)

    valid_keys = [r for r in results if r]
    with open(VALID_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(valid_keys))

    print(f"\n✅ Doğrulama tamamlandı. Geçerli: {len(valid_keys)} | Dosya: {VALID_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
