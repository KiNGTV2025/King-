# generate_m3u_playwright.py
import asyncio
import re
import os
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

# Ayarlar
OUTPUT_M3U = "1UmitTV.m3u"
BASE_CHANNEL_TEST = "yayinzirve"
BASE_PAGE = "https://dengetv66.live/channel?id={channel}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
REFERER = "https://dengetv66.live/"
PROXY_PREFIX = None  # eğer vercel proxy kullanmak istersen: "https://umitdenge.vercel.app/api/proxy?file="

CHANNELS = {
    1: {"file": "yayinzirve.m3u8", "name": "BEIN SPORTS 1 (ZIRVE)"},
    2: {"file": "yayin1.m3u8", "name": "BEIN SPORTS 1 (1)"},
    3: {"file": "yayininat.m3u8", "name": "BEIN SPORTS 1 (INAT)"},
    4: {"file": "yayinb2.m3u8", "name": "BEIN SPORTS 2"},
    5: {"file": "yayinb3.m3u8", "name": "BEIN SPORTS 3"},
    6: {"file": "yayinb4.m3u8", "name": "BEIN SPORTS 4"},
    7: {"file": "yayinb5.m3u8", "name": "BEIN SPORTS 5"},
    8: {"file": "yayinbm1.m3u8", "name": "BEIN SPORTS MAX 1"},
    9: {"file": "yayinbm2.m3u8", "name": "BEIN SPORTS MAX 2"},
    10: {"file": "yayinss.m3u8", "name": "S SPORT PLUS 1"},
    11: {"file": "yayinss2.m3u8", "name": "S SPORT PLUS 2"},
    12: {"file": "yayint1.m3u8", "name": "TIVIBU SPOR 1"},
    13: {"file": "yayint2.m3u8", "name": "TIVIBU SPOR 2"},
    14: {"file": "yayint3.m3u8", "name": "TIVIBU SPOR 3"},
    15: {"file": "yayinsmarts.m3u8", "name": "SPOR SMART 1"},
    16: {"file": "yayinsms2.m3u8", "name": "SPOR SMART 2"},
    17: {"file": "yayintrtspor.m3u8", "name": "TRT SPOR 1"},
    18: {"file": "yayintrtspor2.m3u8", "name": "TRT SPOR 2"},
    19: {"file": "yayintrt1.m3u8", "name": "TRT 1"},
    20: {"file": "yayinas.m3u8", "name": "A SPOR"},
    21: {"file": "yayinatv.m3u8", "name": "ATV"},
    22: {"file": "yayintv8.m3u8", "name": "TV 8"},
    23: {"file": "yayintv85.m3u8", "name": "TV 8.5"},
    24: {"file": "yayinf1.m3u8", "name": "FORMULA 1"},
    25: {"file": "yayinnbatv.m3u8", "name": "NBA TV"},
    26: {"file": "yayineu1.m3u8", "name": "EURO SPORT 1"},
    27: {"file": "yayineu2.m3u8", "name": "EURO SPORT 2"},
    28: {"file": "yayinex1.m3u8", "name": "EXXEN SPOR 1"},
    29: {"file": "yayinex2.m3u8", "name": "EXXEN SPOR 2"},
    30: {"file": "yayinex3.m3u8", "name": "EXXEN SPOR 3"},
    31: {"file": "yayinex4.m3u8", "name": "EXXEN SPOR 4"},
    32: {"file": "yayinex5.m3u8", "name": "EXXEN SPOR 5"},
    33: {"file": "yayinex6.m3u8", "name": "EXXEN SPOR 6"},
    34: {"file": "yayinex7.m3u8", "name": "EXXEN SPOR 7"},
    35: {"file": "yayinex8.m3u8", "name": "EXXEN SPOR 8"},
    36: {"file": "yayinex9.m3u8", "name": "EXXEN SPOR 9"},
}

M3U8_RE = re.compile(r"\.m3u8(?:\?|$)", re.I)

async def find_base_domain(playwright, test_channel=BASE_CHANNEL_TEST, attempts=2, wait_seconds=6):
    for attempt in range(1, attempts+1):
        print(f"► Deneme {attempt}/{attempts} — kanal: {test_channel}")
        try:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=USER_AGENT,
                extra_http_headers={"Referer": REFERER}
            )
            page = await context.new_page()
            requests = []
            page.on("request", lambda req: requests.append(req.url))

            try:
                await page.goto(BASE_PAGE.format(channel=test_channel), wait_until="networkidle", timeout=20000)
            except PWTimeoutError:
                print("  - goto timeout (devam ediliyor)")

            await asyncio.sleep(wait_seconds)

            for url in requests:
                if M3U8_RE.search(url):
                    print("  ✓ .m3u8 isteği bulundu:", url)
                    m = re.match(r"(https?://[^/]+)", url)
                    if m:
                        domain = m.group(1).rstrip('/') + '/'
                        await browser.close()
                        return domain
                    else:
                        if url.startswith("//"):
                            domain = "https:" + url.split("/", 3)[2]
                            await browser.close()
                            return domain
            await browser.close()
            print("  - Bu denemede .m3u8 bulunamadı.")
        except Exception as e:
            print("  - Hata:", e)
    raise RuntimeError("Domain bulunamadı — Playwright ile .m3u8 isteği yakalanamadı.")

def build_m3u(domain, proxy_prefix=None, out_path=OUTPUT_M3U):
    print("► M3U oluşturuluyor... domain=", domain, " proxy_prefix=", proxy_prefix)
    lines = ["#EXTM3U"]
    for cid, data in CHANNELS.items():
        file = data["file"]
        name = data["name"]
        if proxy_prefix:
            stream_url = f"{proxy_prefix}{file}"
        else:
            stream_url = f"{domain.rstrip('/')}/{file.lstrip('/')}"
        lines.append(f'#EXTINF:-1 tvg-id="{cid}" tvg-name="{name}" group-title="Dengetv54",{name}')
        lines.append(f'#EXTVLCOPT:http-user-agent={USER_AGENT}')
        lines.append(f'#EXTVLCOPT:http-referer={REFERER}')
        lines.append(stream_url)
        lines.append("")
    content = "\n".join(lines)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ M3U yazıldı: {out_path}")

async def main():
    async with async_playwright() as p:
        domain = await find_base_domain(p, test_channel=BASE_CHANNEL_TEST, attempts=3, wait_seconds=6)
        print("✅ Bulunan base domain:", domain)
        build_m3u(domain, proxy_prefix=PROXY_PREFIX, out_path=OUTPUT_M3U)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("❌ Hata:", e)
