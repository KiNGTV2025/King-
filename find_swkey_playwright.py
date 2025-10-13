import asyncio
from playwright.async_api import async_playwright
import os

DOMAINS = [f"https://m.prectv{i}.lol" for i in range(60, 70)]  # 60–69 arası dener
SAVE_DIR = "playwright_capture"
SAVE_PATH = os.path.join(SAVE_DIR, "found_swkeys.txt")

async def scrape_domain(page, domain):
    print(f"[i] {domain} adresine gidiliyor...")
    try:
        await page.goto(domain, timeout=30000)
        await page.wait_for_timeout(12000)
        scripts = await page.locator("script").all_inner_texts()
        found = []
        for text in scripts:
            for line in text.splitlines():
                if "0H" in line or "00b" in line or "QWw" in line:
                    found.append(line.strip())
        return found
    except Exception as e:
        print(f"[!] {domain} hatası: {e}")
        return []

async def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    all_found = []

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        page = await browser.new_page()

        for domain in DOMAINS:
            found = await scrape_domain(page, domain)
            if found:
                print(f"[+] {domain} -> {len(found)} aday bulundu")
                all_found.extend([f"{domain} | {k}" for k in found])
            else:
                print(f"[-] {domain} -> hiç anahtar yok")

        await browser.close()

    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(all_found))

    print(f"[i] Tarama tamamlandı. Toplam {len(all_found)} sonuç -> {SAVE_PATH}")

if __name__ == "__main__":
    asyncio.run(main())
