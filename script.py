import json
import urllib.request
import urllib.error
import re
import sys

DEFAULT_BASE_URL = 'https://m.prectv50.sbs'
SOURCE_URL = 'https://raw.githubusercontent.com/kerimmkirac/cs-kerim2/main/RecTV/src/main/kotlin/com/kerimmkirac/RecTV.kt'
API_KEY = '4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452'
SUFFIX = f'/{API_KEY}'

USER_AGENT = 'googleusercontent'
REFERER = 'https://twitter.com/'

def is_base_url_working(base_url: str) -> bool:
    test_url = f"{base_url}/api/channel/by/filtres/0/0/0{SUFFIX}"
    try:
        req = urllib.request.Request(
            test_url,
            headers={'User-Agent': 'okhttp/4.12.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except:
        return False

def get_dynamic_base_url() -> str:
    try:
        with urllib.request.urlopen(SOURCE_URL) as response:
            content = response.read().decode('utf-8')
            if match := re.search(r'override\s+var\s+mainUrl\s*=\s*"([^"]+)"', content):
                return match.group(1)
    except Exception as e:
        print(f"GitHub'dan URL alınamadı: {e}", file=sys.stderr)
    return DEFAULT_BASE_URL

def fetch_data(url: str):
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': USER_AGENT,
                'Referer': REFERER
            }
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"API hatası ({url}): {e}", file=sys.stderr)
        return None

def main():
    base_url = DEFAULT_BASE_URL if is_base_url_working(DEFAULT_BASE_URL) else get_dynamic_base_url()
    print(f"Kullanılan Base URL: {base_url}", file=sys.stderr)

    all_data = {
        "channels": [],
        "movies": [],
        "series": []
    }

    # Canlı yayınlar (0-3)
    for page in range(4):
        url = f"{base_url}/api/channel/by/filtres/0/0/{page}{SUFFIX}"
        data = fetch_data(url)
        if data:
            all_data["channels"].extend(data)

    # Filmler - kategoriler
    movie_categories = ["0", "14", "1", "13", "19", "4", "2", "10", "3", "8", "17", "5"]
    for category_id in movie_categories:
        for page in range(8):
            url = f"{base_url}/api/movie/by/filtres/{category_id}/created/{page}{SUFFIX}"
            data = fetch_data(url)
            if data:
                all_data["movies"].extend(data)

    # Diziler (0-7)
    for page in range(8):
        url = f"{base_url}/api/serie/by/filtres/0/created/{page}{SUFFIX}"
        data = fetch_data(url)
        if data:
            all_data["series"].extend(data)

    # JSON dosyaya yaz
    with open('qdene.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print("qdene.json dosyası oluşturuldu.", file=sys.stderr)

if __name__ == "__main__":
    main()
