import json
import urllib.request
import urllib.error
import re
import sys
from typing import Dict, List, Optional

DEFAULT_BASE_URL = 'https://m.prectv50.sbs'
SOURCE_URL = 'https://raw.githubusercontent.com/kerimmkirac/cs-kerim2/main/RecTV/src/main/kotlin/com/kerimmkirac/RecTV.kt'
API_KEY = '4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a3688a30452'
SUFFIX = f'/{API_KEY}'

USER_AGENT = 'googleusercontent'
REFERER = 'https://twitter.com/'

def is_base_url_working(base_url: str) -> bool:
    test_url = f"{base_url}/api/channel/by/filtres/0/0/0{SUFFIX}"
    try:
        req = urllib.request.Request(test_url, headers={'User-Agent': 'okhttp/4.12.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except:
        return False

def get_dynamic_base_url() -> str:
    try:
        with urllib.request.urlopen(SOURCE_URL) as response:
            content = response.read().decode('utf-8')
            match = re.search(r'override\s+var\s+mainUrl\s*=\s*"([^"]+)"', content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"GitHub'dan URL alınamadı: {e}", file=sys.stderr)
    return DEFAULT_BASE_URL

def fetch_data(url: str) -> Optional[List[Dict]]:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Referer': REFERER})
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"API hatası ({url}): {e}", file=sys.stderr)
        return None

def process_content(content: Dict, category_name: str) -> List[Dict]:
    """İçeriği JSON formatına uygun şekilde hazırla."""
    items = []
    if not content.get('sources'):
        return items

    for source in content['sources']:
        if source.get('type') == 'm3u8' and source.get('url'):
            items.append({
                "id": content.get('id', ''),
                "title": content.get('title', ''),
                "logo": content.get('image', ''),
                "category": category_name,
                "quality": source.get('quality', ''),
                "url": source.get('url')
            })
    return items

def main():
    base_url = DEFAULT_BASE_URL if is_base_url_working(DEFAULT_BASE_URL) else get_dynamic_base_url()
    print(f"Kullanılan Base URL: {base_url}", file=sys.stderr)

    all_channels = []

    # CANLI YAYINLAR (0-3 arası sayfalar)
    for page in range(4):
        url = f"{base_url}/api/channel/by/filtres/0/0/{page}{SUFFIX}"
        data = fetch_data(url)
        if data:
            for content in data:
                all_channels.extend(process_content(content, "Canlı Yayınlar"))

    # FİLMLER
    movie_categories = {
        "0": "Son Filmler", "14": "Aile", "1": "Aksiyon", "13": "Animasyon",
        "19": "Belgesel Filmleri", "4": "Bilim Kurgu", "2": "Dram",
        "10": "Fantastik", "3": "Komedi", "8": "Korku", "17": "Macera",
        "5": "Romantik"
    }
    for cat_id, cat_name in movie_categories.items():
        for page in range(8):
            url = f"{base_url}/api/movie/by/filtres/{cat_id}/created/{page}{SUFFIX}"
            data = fetch_data(url)
            if data:
                for content in data:
                    all_channels.extend(process_content(content, cat_name))

    # DİZİLER
    for page in range(8):
        url = f"{base_url}/api/serie/by/filtres/0/created/{page}{SUFFIX}"
        data = fetch_data(url)
        if data:
            for content in data:
                all_channels.extend(process_content(content, "Son Diziler"))

    # JSON dosyasına kaydet
    with open("qdene.json", "w", encoding="utf-8") as f:
        json.dump(all_channels, f, ensure_ascii=False, indent=2)

    print("qdene.json dosyası başarıyla oluşturuldu!", file=sys.stderr)

if __name__ == "__main__":
    main()
