import asyncio
from playwright.async_api import async_playwright
import aiohttp
import os

SAVE_DIR = "playwright_capture"
SAVE_PATH = os.path.join(SAVE_DIR, "found_swkeys.txt")

# 50–80 arası domainleri deneyecek
BASE_DOMAINS = [f"m.prectv{i}.lol" for i in range(50, 81)] + [f"m.prectv{i}.com" for i in range(50, 81)]


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
                    found.append(line.strip())
        return found
    except Exception as e:
        print(f"[!] {domain} hata: {e}")
        return []


async def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    all_found = []

    active_domains = await find_active_domains()
    if not active_domains:
        print("[x] Hiç aktif domain bulunamadı.")
        return

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        page = await browser.new_page()

        for domain in active_domains:
            found = await scrape_domain(page, domain)
            if found:
                print(f"[+] {domain} -> {len(found)} anahtar bulundu.")
                all_found.extend([f"{domain} | {k}" for k in found])
            else:
                print(f"[-] {domain} -> anahtar bulunamadı.")

        await browser.close()

    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(all_found))

    print(f"\n✅ Tarama tamamlandı. {len(all_found)} sonuç bulundu → {SAVE_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
