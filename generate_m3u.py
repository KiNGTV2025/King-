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
        }

    async def get_base_domain(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            requests = []

            # Ağ isteklerini dinle
            page.on("request", lambda request: requests.append(request.url))

            await page.goto("https://dengetv66.live/channel?id=yayinzirve", wait_until="networkidle")

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
