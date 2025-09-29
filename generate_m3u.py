import asyncio
from playwright.async_api import async_playwright

class Dengetv54Manager:
    def __init__(self, m3u_path="1UmitTV.m3u"):
        self.m3u_path = m3u_path
        self.proxy_url = "https://umittv-denge54.umitm0d.workers.dev/"
        self.referer = "https://dengetv66.live/"
        self.channels = {
            1: {"file": "yayinzirve.m3u8", "name": "BEIN SPORTS 1 (ZIRVE)"},
            2: {"file": "yayin1.m3u8", "name": "BEIN SPORTS 1 (1)"},
            3: {"file": "yayininat.m3u8", "name": "BEIN SPORTS 1 (INAT)"},
            # ... diğer kanallar ...
        }

    async def get_base_domain(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            requests = []

            # Ana sayfa requestlerini dinle
            page.on("request", lambda request: requests.append(request.url))

            await page.goto("https://dengetv66.live/channel?id=yayinzirve", wait_until="networkidle")

            # iframe varsa onları da kontrol et
            for frame in page.frames:
                frame.on("request", lambda request: requests.append(request.url))

            # Küçük bir bekleme, iframe yüklenir
            await asyncio.sleep(2)

            domain = None
            for url in requests:
                if ".m3u8" in url:
                    print("🎯 Bulundu:", url)
                    domain = url.split("/yayinzirve.m3u8")[0] + "/"
                    break

            await browser.close()

            if not domain:
                raise Exception("❌ Domain bulunamadı!")
            return domain

    async def generate_m3u(self):
        base_domain = await self.get_base_domain()
        lines = ["#EXTM3U"]

        for channel_id, data in self.channels.items():
            original_url = f"{base_domain}{data['file']}"
            proxy_url = f"{self.proxy_url}?url={original_url}"
            lines.extend([
                f'#EXTINF:-1 tvg-id="{channel_id}" tvg-name="{data["name"]}" group-title="Dengetv54",{data["name"]}',
                f'#EXTVLCOPT:http-referer={self.referer}',
                proxy_url,
                ""
            ])
        return "\n".join(lines)

    async def update_m3u(self):
        try:
            content = await self.generate_m3u()
            with open(self.m3u_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ M3U güncellendi: {self.m3u_path}")
        except Exception as e:
            print(f"❌ Hata: {e}")

if __name__ == "__main__":
    manager = Dengetv54Manager()
    asyncio.run(manager.update_m3u())
